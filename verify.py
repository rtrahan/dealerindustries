from app.config import load_config
from app.aggregator import build_report

config = load_config()
with open('/Users/roberttrahan/Downloads/Tekion Advisor Performance Report.xlsx','rb') as a:
    advisor = a.read()
with open('/Users/roberttrahan/Downloads/Tekion OP Code History Report.csv','rb') as o:
    opcode = o.read()

report = build_report(advisor, opcode, config)

print('=== ADVISOR METRICS FROM EXCEL ===')
for r in report.advisors:
    print(f'{r.name}: CP ROs={r.cp_ro_cnt}, ELR=${r.elr:.2f}, Parts GP={r.mp_pct}%')

print('\n=== KIT COUNTS FROM CSV ===')
for r in report.advisors:
    counts = {k: v for k,v in r.kit_counts.items() if v > 0}
    print(f'{r.name}: {counts}')

print('\n=== REVENUE CALCULATION ===')
for r in report.advisors:
    rev = 0
    for code, qty in r.kit_counts.items():
        if qty > 0:
            price = next(k.price for k in config.kits if k.code == code)
            rev += qty * price
            print(f'  {r.name} sold {qty}x {code} @ ${price} = ${qty*price:.2f}')
    print(f'  {r.name} Total: ${rev:.2f} (Matches report: {rev == r.revenue})')
