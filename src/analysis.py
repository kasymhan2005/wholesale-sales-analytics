"""Reproducible sales analysis. Revenue is the course-defined gross order value."""
from pathlib import Path
import json
import unicodedata
import pandas as pd


def require(condition, message):
    if not condition:
        raise ValueError(message)


def load_data(raw):
    raw = Path(raw)
    buckets = {k: [] for k in ('orders', 'order_status', 'products')}
    manifest = []
    expected = {'orders': ['order_id', 'product_id', 'quantity'],
                'order_status': ['order_id', 'client_id', 'status'],
                'products': ['id', 'name', 'price']}
    for path in sorted((raw / 'data').rglob('*.csv')):
        kind = path.stem
        if kind not in buckets:
            continue
        df = pd.read_csv(path)
        require(list(df.columns) == expected[kind], f'Unexpected schema: {path}')
        require(not df.isna().any().any(), f'Missing values: {path}')
        manifest.append({'file': str(path.relative_to(raw)), 'rows': len(df), 'table': kind})
        if kind == 'orders':
            df['manager'] = unicodedata.normalize('NFC', path.parent.name)
            df['date'] = pd.to_datetime(path.parent.parent.name, format='%Y-%m-%d')
        if kind == 'products':
            df['category'] = unicodedata.normalize('NFC', path.parent.name)
        buckets[kind].append(df)
    require(all(buckets.values()), 'Missing orders, status or product input files')
    orders, status, products = [pd.concat(buckets[k], ignore_index=True) for k in buckets]
    orders = orders.sort_values(['order_id', 'product_id']).reset_index(drop=True)
    status = status.sort_values('order_id').reset_index(drop=True)
    products = products.sort_values('id').reset_index(drop=True)
    require(not status.order_id.duplicated().any(), 'Duplicate status order IDs')
    require(not products.id.duplicated().any(), 'Duplicate product IDs')
    require(not orders.duplicated(['order_id', 'product_id']).any(), 'Duplicate order/product lines')
    require(set(status.status) <= {'confirmed', 'canceled'}, 'Unknown status')
    require((orders.quantity > 0).all() and (orders.quantity % 1 == 0).all(), 'Invalid quantity')
    require((products.price > 0).all(), 'Invalid product price')
    require(set(orders.order_id) == set(status.order_id), 'Order/status key mismatch')
    require(set(orders.product_id) <= set(products.id), 'Unknown product')
    for col in ('date', 'manager'):
        require(orders.groupby('order_id')[col].nunique().eq(1).all(), f'Conflicting {col}')
    currency = pd.read_csv(raw / 'usd_rate.txt', header=None,
                           names=['date', 'currency_rate', 'currency'])
    currency['date'] = pd.to_datetime(currency.date, format='%Y-%m-%d')
    require(not currency.isna().any().any(), 'Missing exchange-rate values')
    require(not currency.date.duplicated().any(), 'Duplicate rate dates')
    require((currency.currency_rate > 0).all(), 'Invalid rate')
    full = orders.merge(status, on='order_id', validate='many_to_one')
    full = full.merge(products, left_on='product_id', right_on='id', validate='many_to_one')
    full = full.merge(currency[['date', 'currency_rate']], on='date', how='left', validate='many_to_one')
    require(full.currency_rate.notna().all(), 'Missing daily rate')
    require(len(full) == len(orders), 'Join changed line count')
    full['brand'] = full.name.str.split(',').str[0].str.strip()
    full['price_rub'] = full.price * full.currency_rate
    full['revenue'] = full.price_rub * full.quantity
    products['brand'] = products.name.str.split(',').str[0].str.strip()
    return full, products, currency, pd.DataFrame(manifest)


def order_table(full):
    """One row per order, including canceled basket values (not revenue)."""
    return full.groupby('order_id', as_index=False).agg(
        date=('date', 'first'), manager=('manager', 'first'), client_id=('client_id', 'first'),
        status=('status', 'first'), order_value=('revenue', 'sum'),
        units=('quantity', 'sum'), unique_products=('product_id', 'nunique'))


def match_reorders(full):
    """Exact basket + client + manager, next day; deterministic one-to-one pairing.

    Multiple indistinguishable baskets are labeled ambiguous, not proven matches.
    Pairing rank prevents a many-to-many join from inflating the count.
    """
    orders = order_table(full)
    baskets = full.groupby('order_id')[['product_id', 'quantity']].apply(
        lambda g: json.dumps(sorted(zip(g.product_id.astype(int), g.quantity.astype(int)))))
    orders['basket'] = orders.order_id.map(baskets)
    keys = ['client_id', 'manager', 'basket', 'match_date']
    old = orders[orders.status.eq('canceled')].copy()
    new = orders[orders.status.eq('confirmed')].copy()
    old['match_date'] = old.date + pd.Timedelta(days=1)
    new['match_date'] = new.date
    for df in (old, new):
        df.sort_values('order_id', inplace=True)
        df['rank'] = df.groupby(keys).cumcount()
        df['candidates'] = df.groupby(keys).order_id.transform('size')
    pairs = old.merge(new, on=keys + ['rank'], suffixes=('_canceled', '_confirmed'))
    pairs['ambiguous'] = (pairs.candidates_canceled > 1) | (pairs.candidates_confirmed > 1)
    return pairs


def abc_classify(products):
    """Classify positive sales by cumulative revenue BEFORE each item.

    The item crossing 80% belongs to A; the one crossing 95% belongs to B.
    Zero-sales items have their own class. Ties are ordered by product ID.
    """
    result = products.sort_values(['revenue', 'id'], ascending=[False, True]).copy()
    total = result.revenue.sum()
    result['revenue_share'] = result.revenue / total if total else 0.0
    result['cumulative_share'] = result.revenue_share.cumsum()
    prior = result.cumulative_share - result.revenue_share
    result['abc'] = 'C'
    result.loc[prior < .95, 'abc'] = 'B'
    result.loc[prior < .80, 'abc'] = 'A'
    result.loc[result.revenue.eq(0), 'abc'] = 'No sales'
    return result


def analyze(full, products):
    orders = order_table(full)
    sold = full[full.status.eq('confirmed')]
    confirmed = orders[orders.status.eq('confirmed')]
    dates = pd.date_range(full.date.min(), full.date.max(), freq='D')
    daily = orders.groupby(['date', 'status']).size().unstack(fill_value=0)
    daily = daily.reindex(index=dates, columns=['confirmed', 'canceled'], fill_value=0)
    daily['revenue'] = confirmed.groupby('date').order_value.sum().reindex(dates, fill_value=0)
    daily['average_order_value'] = daily.revenue / daily.confirmed.replace(0, float('nan'))
    daily.index.name = 'date'
    daily = daily.reset_index()
    def grouped(key):
        return sold.groupby(key, as_index=False).agg(revenue=('revenue','sum'),
            orders=('order_id','nunique'), units=('quantity','sum')).sort_values('revenue', ascending=False)
    brands, categories, clients = [grouped(k) for k in ('brand', 'category', 'client_id')]
    managers = orders.groupby('manager').agg(total_orders=('order_id','size'),
        canceled=('status', lambda x: x.eq('canceled').sum()))
    managers = managers.join(confirmed.groupby('manager').agg(
        confirmed=('order_id','size'), revenue=('order_value','sum'))).fillna(0)
    managers['cancel_rate'] = managers.canceled / managers.total_orders
    managers['average_order_value'] = managers.revenue / managers.confirmed.replace(0, float('nan'))
    managers['revenue_share'] = managers.revenue / managers.revenue.sum()
    managers['order_share'] = managers.confirmed / managers.confirmed.sum()
    managers = managers.sort_values('revenue', ascending=False).reset_index()
    product_sales = products.merge(sold.groupby('product_id', as_index=False).agg(
        revenue=('revenue','sum'), orders=('order_id','nunique'), units=('quantity','sum')),
        left_on='id', right_on='product_id', how='left', validate='one_to_one')
    product_sales[['revenue','orders','units']] = product_sales[['revenue','orders','units']].fillna(0)
    product_sales['is_in_orders'] = product_sales.orders.gt(0)
    product_sales = abc_classify(product_sales.drop(columns='product_id'))
    coverage = product_sales.groupby('brand', as_index=False).agg(
        products=('id','size'), sold_products=('is_in_orders','sum'))
    coverage['unsold_products'] = coverage.products - coverage.sold_products
    coverage['unsold_share'] = coverage.unsold_products / coverage.products
    coverage = coverage.sort_values('unsold_share', ascending=False)
    clients['revenue_share'] = clients.revenue / clients.revenue.sum()
    clients['cumulative_share'] = clients.revenue_share.cumsum()
    pairs = match_reorders(full)
    summary = dict(lines=len(full), orders=len(orders), products=len(products),
        confirmed_orders=len(confirmed), canceled_orders=int(orders.status.eq('canceled').sum()),
        cancel_rate=float(orders.status.eq('canceled').mean()),
        revenue=float(sold.revenue.sum()), average_order_value=float(confirmed.order_value.mean()),
        sold_products=int(product_sales.is_in_orders.sum()),
        unsold_products=int((~product_sales.is_in_orders).sum()),
        active_clients=len(clients), top5_client_share=float(clients.head(5).revenue_share.sum()),
        exact_next_day_pairs=len(pairs), ambiguous_pairs=int(pairs.ambiguous.sum()),
        matched_confirmed_value=float(pairs.order_value_confirmed.sum()),
        leading_brand=str(brands.iloc[0].brand), leading_manager=str(managers.iloc[0].manager))
    return dict(summary=summary, orders=orders, daily=daily, brands=brands,
                categories=categories, clients=clients, managers=managers,
                product_sales=product_sales, coverage=coverage, pairs=pairs)
