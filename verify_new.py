from app.config import load_config
from app.aggregator import build_report

config = load_config('1_6197')
with open('/Users/roberttrahan/Downloads/Advisor Performance Report (1).xlsx','rb') as a:
    advisor = a.read()
with open('/Users/roberttrahan/Downloads/Detailed Sales Report 0601-0616 2026.csv','rb') as o:
    opcode = o.read()

report = build_report(advisor, opcode, config)

print('=== ADVISOR METRICS FROM EXCEL ===')
for r in report.advisors:
    print(f'{r.name}: CP ROs={r.cp_ro_cnt}, ELR=${r.elr:.2f}, Parts GP={r.mp_pct}%')

print('\n=== KIT COUNTS FROM CSV ===')
for r in report.advisors:
    counts = {k: v for k,v in r.kit_counts.items() if v > 0}
    print(f'{r.name}: {counts}')
