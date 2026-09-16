#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""حساب معدلات نشر المستويات (publishes/sec) من لقطتَي evidence() على الجهاز.
الـ peak تراكمي (أقصى قيمة منذ إنشاء النموذج) — لا يُحسب كدلتا.

الاستخدام:
  python3 Tools/level_evidence_calc.py \
    "LEVELS micPublishes=120 outPublishes=80 micPeak=0.045 outPeak=0.612" \
    "LEVELS micPublishes=540 outPublishes=310 micPeak=0.091 outPeak=0.612" \
    21.0

(لقطة بداية المرحلة، لقطة نهاية المرحلة، المدة بالثواني)
"""
import sys, re

def parse(ev):
    m = re.search(r'micPublishes=(\d+)\s+outPublishes=(\d+)\s+micPeak=([\d.]+)\s+outPeak=([\d.]+)', ev)
    if not m:
        return None
    return dict(mic=int(m.group(1)), out=int(m.group(2)),
                micPeak=float(m.group(3)), outPeak=float(m.group(4)))

def main():
    if len(sys.argv) != 4:
        print(__doc__)
        sys.exit(2)
    a, b, dur = parse(sys.argv[1]), parse(sys.argv[2]), float(sys.argv[3])
    if not a or not b or dur <= 0:
        print("لقطة غير صالحة أو مدة ≤ 0")
        sys.exit(2)
    d_mic = b['mic'] - a['mic']
    d_out = b['out'] - a['out']
    print(f"مدة المرحلة: {dur:.1f}s")
    print(f"mic   publishes: {a['mic']} -> {b['mic']}  (delta {d_mic})  => {d_mic/dur:.1f}/s")
    print(f"out   publishes: {a['out']} -> {b['out']}  (delta {d_out})  => {d_out/dur:.1f}/s")
    print(f"micPeak  (تراكمي، أقصى منذ الإطلاق): {a['micPeak']:.3f} -> {b['micPeak']:.3f}")
    print(f"outPeak  (تراكمي، أقصى منذ الإطلاق): {a['outPeak']:.3f} -> {b['outPeak']:.3f}")
    print("\nملاحظة: الـ peak تراكمي — لعزل peak مرحلة معيّنة، أعد تشغيل التطبيق قبلها.")

if __name__ == '__main__':
    main()
