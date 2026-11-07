"""Run from any directory: python /path/to/run_analysis.py."""
from pathlib import Path
import json
import sys
import platform
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import pandas as pd
from src.analysis import load_data, analyze

ROOT = Path(__file__).resolve().parent


def main():
    out = ROOT / 'reports'
    out.mkdir(exist_ok=True)
    full, products, currency, manifest = load_data(ROOT / 'data/raw')
    results = analyze(full, products)
    manifest.to_csv(out / 'input_manifest.csv', index=False)
    full.to_csv(out / 'order_lines.csv', index=False)
    for name, value in results.items():
        if isinstance(value, pd.DataFrame):
            value.to_csv(out / f'{name}.csv', index=False)
    summary = results['summary']
    summary['source_csv_files'] = len(manifest)
    summary['mean_usd_rate'] = float(currency.currency_rate.mean())
    (out / 'summary.json').write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding='utf-8')
    (out / 'validation.json').write_text(json.dumps({'status':'passed',
        'checks':['schemas', 'required values', 'unique dimension keys', 'unique order/product lines',
                  'valid statuses', 'positive prices and integer quantities', 'foreign keys',
                  'consistent order dates/managers', 'unique positive daily exchange rates',
                  'rate coverage', 'row-preserving many-to-one joins'],
        'python':platform.python_version(), 'pandas':pd.__version__, 'matplotlib':matplotlib.__version__}, indent=2))
    plt.rcParams.update({'font.family':'DejaVu Sans','axes.spines.top':False,
        'axes.spines.right':False,'axes.titleweight':'bold','figure.facecolor':'white'})
    daily = results['daily']
    fig, axes = plt.subplots(3, 1, figsize=(11, 9), sharex=True)
    axes[0].plot(daily.date, daily.confirmed, label='Confirmed', color='#168a8c')
    axes[0].plot(daily.date, daily.canceled, label='Canceled', color='#d78c35')
    axes[0].legend(); axes[0].set_title('Daily orders and confirmed sales | March 2024');axes[0].set_ylabel('Distinct orders')
    axes[1].plot(daily.date, daily.revenue/1e6, color='#168a8c');axes[1].set_ylabel('Revenue (RUB m)')
    axes[2].plot(daily.date, daily.average_order_value/1e6, color='#315e83');axes[2].set_ylabel('Average order (RUB m)')
    for ax in axes:ax.grid(alpha=.18)
    fig.autofmt_xdate();fig.tight_layout();fig.savefig(out/'daily_sales.png',dpi=160);plt.close(fig)
    fig, axes=plt.subplots(1,2,figsize=(13,6))
    for ax,key,label in zip(axes,['brands','categories'],['brand','category']):
        top=results[key].head(10).iloc[::-1];ax.barh(top[label],top.revenue/1e6,color='#168a8c');ax.set_xlabel('Confirmed revenue (RUB m)');ax.set_title('Top '+key)
    fig.tight_layout();fig.savefig(out/'assortment.png',dpi=160);plt.close(fig)
    html=(ROOT/'src/dashboard.html').read_text(encoding='utf-8')
    export=full.copy();export['date']=export.date.dt.strftime('%Y-%m-%d')
    abc=results['product_sales'].groupby('abc',as_index=False).agg(products=('id','size'),revenue=('revenue','sum'))
    abc['share']=abc.revenue/abc.revenue.sum()
    replacements={'__DATA__':export.to_json(orient='records',force_ascii=False),
        '__SUMMARY__':json.dumps(summary,ensure_ascii=False),'__ABC__':abc.to_json(orient='records'),
        '__CLIENTS__':results['clients'].to_json(orient='records')}
    for key,value in replacements.items():html=html.replace(key,value.replace('</','<\\/'))
    (out/'dashboard.html').write_text(html,encoding='utf-8')
    print(json.dumps(summary,ensure_ascii=False,indent=2))
    return results

if __name__ == '__main__':
    main()
