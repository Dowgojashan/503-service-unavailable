import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch
import os

os.makedirs('outputs/figures', exist_ok=True)

fig, ax = plt.subplots(figsize=(9, 14))
ax.set_xlim(0, 14)
ax.set_ylim(0, 22)
ax.axis('off')
plt.subplots_adjust(left=0.06, right=0.99, top=0.99, bottom=0.01)

# ── Helpers ───────────────────────────────────────────────────────────────────

def rbox(cx, cy, w, h, text, fc='white', ec='#444444', fs=14, lw=1.3):
    ax.add_patch(FancyBboxPatch(
        (cx - w/2, cy - h/2), w, h,
        boxstyle='round,pad=0.09', facecolor=fc, edgecolor=ec,
        linewidth=lw, zorder=3))
    ax.text(cx, cy, text, ha='center', va='center', fontsize=fs,
            zorder=4, multialignment='center')

def dmd(cx, cy, w, h, text, fc='#FFF3CD', ec='#856404', fs=13):
    ax.add_patch(plt.Polygon(
        [(cx, cy+h/2), (cx+w/2, cy), (cx, cy-h/2), (cx-w/2, cy)],
        facecolor=fc, edgecolor=ec, linewidth=1.3, zorder=3))
    ax.text(cx, cy, text, ha='center', va='center', fontsize=fs,
            zorder=4, multialignment='center')

def bar(x1, x2, y):
    ax.add_patch(mpatches.Rectangle(
        (x1, y - 0.06), x2 - x1, 0.12,
        facecolor='#2C3E50', edgecolor='#2C3E50', zorder=3))

def arr(x1, y1, x2, y2, lw=1.2):
    ax.annotate('', xy=(x2, y2), xytext=(x1, y1),
                arrowprops=dict(arrowstyle='->', color='#333333', lw=lw),
                zorder=2)

def lbl(x, y, text, ha='center', c='#555555', fs=13, bold=False):
    ax.text(x, y, text, ha=ha, va='center', fontsize=fs, color=c,
            fontweight='bold' if bold else 'normal', zorder=5)

def phase_bg(yb, h, title, fc, ec):
    ax.add_patch(FancyBboxPatch(
        (0.5, yb), 13.0, h, boxstyle='round,pad=0.1',
        facecolor=fc, edgecolor=ec, linewidth=2, alpha=0.35, zorder=1))
    ax.text(0.87, yb + h/2, title, ha='center', va='center',
            fontsize=12, fontweight='bold', color=ec, rotation=90, zorder=2)

# ── Phase backgrounds ─────────────────────────────────────────────────────────
phase_bg(17.3, 4.4,  'Phase 1\nData Prep',  '#D6EAF8', '#2E86C1')
phase_bg(10.2, 6.9,  'Phase 2\nPrompt Dev', '#D5F5E3', '#27AE60')
phase_bg( 3.1, 6.9,  'Phase 3\nExperiment', '#FEF9E7', '#D4AC0D')
phase_bg( 0.1, 2.8,  'Phase 4\nAnalysis',   '#F5EEF8', '#8E44AD')

# ── START ─────────────────────────────────────────────────────────────────────
ax.add_patch(plt.Circle((7, 21.55), 0.22, color='#2C3E50', zorder=3))
arr(7, 21.33, 7, 20.95)

# ── PHASE 1 ───────────────────────────────────────────────────────────────────
rbox(7, 20.65, 4.2, 0.52, 'Select Dataset')
arr(7, 20.39, 7, 19.99)
rbox(7, 19.68, 5.8, 0.60, 'Label Difficulty\n(Easy / Medium / Hard)')
arr(7, 19.38, 7, 18.98)
rbox(7, 18.67, 4.2, 0.52, 'Generate Fact Sheet')
arr(7, 18.41, 7, 18.01)
rbox(7, 17.70, 6.8, 0.62, 'Pilot (15)  /  IS Eval (150)  /  OOS (50)',
     fs=13)

# ── PHASE 2 ───────────────────────────────────────────────────────────────────
arr(7, 17.39, 7, 16.98)
rbox(7, 16.67, 4.6, 0.52, 'Load Pilot Set  (15 cases)')
arr(7, 16.41, 7, 16.01)
rbox(7, 15.70, 5.8, 0.52, '× 4 Architectures  ×  3 Personas')
arr(7, 15.44, 7, 15.04)
rbox(7, 14.73, 4.4, 0.52, 'Run Agent Simulation')
arr(7, 14.47, 7, 14.07)
rbox(7, 13.76, 4.2, 0.52, 'Evaluate S_Agent')
arr(7, 13.50, 7, 12.93)
dmd(7, 11.80, 4.6, 1.12, 'All 4 arch\npassing?')

# "No" → Refine Prompts → loop back
arr(9.3, 11.80, 10.45, 11.80)
lbl(9.7, 11.98, 'No', c='#c0392b', fs=12)
rbox(11.35, 11.80, 1.8, 0.55, 'Refine\nPrompts', fc='#FDECEA', ec='#c0392b')
ax.annotate('', xy=(9.2, 14.73), xytext=(12.25, 11.80),
            arrowprops=dict(arrowstyle='->', color='#333333', lw=1.2,
                            connectionstyle='arc3,rad=-0.3'), zorder=2)

# "Yes" → down to fork
arr(7, 11.24, 7, 10.48)
lbl(7.20, 10.86, 'Yes', c='#27AE60', fs=12)

# ── PHASE 3 ───────────────────────────────────────────────────────────────────
bar(3.5, 10.5, 10.42)
arr(3.5,  10.36, 3.5,  10.02)
arr(10.5, 10.36, 10.5, 10.02)

# IS column ───────────────────────────────────────────────────────────────────
rbox(3.5, 9.84, 3.8, 0.44, 'IS: 150 cases', fc='#D6EAF8', ec='#2E86C1', fs=12)
rbox(3.5, 9.46, 3.4, 0.52, '× 4 Architectures', fs=13)
arr(3.5, 9.20, 3.5, 8.82)
bar(1.1, 5.9, 8.76)
arr(1.9, 8.70, 1.9, 8.38);  rbox(1.9, 8.10, 1.5, 0.48, 'Polite',      fs=11)
arr(3.5, 8.70, 3.5, 8.38);  rbox(3.5, 8.10, 1.5, 0.48, 'Adversarial', fs=10)
arr(5.1, 8.70, 5.1, 8.38);  rbox(5.1, 8.10, 1.5, 0.48, 'VIP',         fs=11)
arr(1.9, 7.86, 1.9, 7.52)
arr(3.5, 7.86, 3.5, 7.52)
arr(5.1, 7.86, 5.1, 7.52)
bar(1.1, 5.9, 7.46)
arr(3.5, 7.40, 3.5, 7.04)
rbox(3.5, 6.74, 3.4, 0.58, 'Run Simulation\n(1,800 convs)',            fs=12)
arr(3.5, 6.45, 3.5, 6.09)
rbox(3.5, 5.79, 3.4, 0.58, 'Evaluate Conversation\n→ S_Agent, ProxyCost', fs=11)

# OOS column ──────────────────────────────────────────────────────────────────
rbox(10.5, 9.84, 3.8, 0.44, 'OOS: 50 cases', fc='#FEF9E7', ec='#D4AC0D', fs=12)
rbox(10.5, 9.46, 3.4, 0.52, '× 4 Architectures', fs=13)
arr(10.5, 9.20, 10.5, 8.82)
bar(8.1, 12.9, 8.76)
arr( 8.9, 8.70,  8.9, 8.38);  rbox( 8.9, 8.10, 1.5, 0.48, 'Polite',      fs=11)
arr(10.5, 8.70, 10.5, 8.38);  rbox(10.5, 8.10, 1.5, 0.48, 'Adversarial', fs=10)
arr(12.1, 8.70, 12.1, 8.38);  rbox(12.1, 8.10, 1.5, 0.48, 'VIP',         fs=11)
arr( 8.9, 7.86,  8.9, 7.52)
arr(10.5, 7.86, 10.5, 7.52)
arr(12.1, 7.86, 12.1, 7.52)
bar(8.1, 12.9, 7.46)
arr(10.5, 7.40, 10.5, 7.04)
rbox(10.5, 6.74, 3.4, 0.58, 'Run Simulation\n(600 convs)',              fs=12)
arr(10.5, 6.45, 10.5, 6.09)
rbox(10.5, 5.79, 3.4, 0.58, 'Evaluate Conversation\n→ S_Agent, ProxyCost', fs=11)

# IS / OOS join bar
arr( 3.5, 5.50,  3.5, 3.76)
arr(10.5, 5.50, 10.5, 3.76)
bar(3.5, 10.5, 3.70)
arr(7, 3.64, 7, 3.25)

# ── PHASE 4 ───────────────────────────────────────────────────────────────────
rbox(7, 2.96, 5.6, 0.52, 'Compute  NetValue  &  ΔMB')
arr(7, 2.70, 7, 2.34)
bar(3.5, 10.5, 2.28)
arr(4.6,  2.22, 3.5,  1.88)
arr(9.4,  2.22, 10.5, 1.88)
rbox( 3.5, 1.58, 3.4, 0.56, 'Weight Sensitivity\n(969 combinations)', fs=11)
rbox(10.5, 1.58, 3.0, 0.56, 'PSS Analysis\n(ProSA)',                  fs=12)
arr( 3.5, 1.30,  3.5, 0.96)
arr(10.5, 1.30, 10.5, 0.96)
bar(3.5, 10.5, 0.90)
arr(7, 0.84, 7, 0.58)

# END (bullseye)
ax.add_patch(plt.Circle((7, 0.36), 0.20, color='#2C3E50', zorder=3))
ax.add_patch(plt.Circle((7, 0.36), 0.12, color='white',   zorder=4))

plt.savefig('outputs/figures/experiment_flow.png', dpi=150,
            bbox_inches='tight', facecolor='white')
plt.close()
print("Saved: outputs/figures/experiment_flow.png")
