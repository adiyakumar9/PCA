"""
analyze_p3.py — Analyze Phase 3 A/B/C Testing results.
Compares Control vs. Simple Belief vs. Reflexive Grounding.
"""

from db import get_connection

def analyze_p3():
    with get_connection() as conn:
        print("\n" + "═"*72)
        print("  PHASE 3: REFLEXIVE GROUNDING ANALYSIS")
        print("═"*72)
        
        # 1. Overall Comparison
        stats = conn.execute("""
            SELECT 
                experiment_group,
                COUNT(*) as runs,
                SUM(actual_success) as wins,
                AVG(actual_success) as rate,
                AVG(execution_time_ms) as avg_time
            FROM logs
            WHERE experiment_group IN ('control', 'belief', 'reflection')
            GROUP BY experiment_group
            ORDER BY rate DESC
        """).fetchall()
        
        if not stats:
            print("No Phase 3 data found in logs.")
            return

        print(f"  {'GROUP':<15} {'RUNS':<8} {'SUCCESS':<12} {'RATE':<10} {'AVG TIME':<10}")
        print("  " + "─"*65)
        
        for row in stats:
            print(f"  {row['experiment_group'].upper():<15} {row['runs']:<8} "
                  f"{row['wins']:<12} {row['rate']:.1%}      {row['avg_time']:.0f}ms")
        
        # 2. Reflection Content Audit
        print("\n  SAMPLE REFLECTIONS (Group: REFLECTION)")
        print("  " + "─"*65)
        reflections = conn.execute("""
            SELECT task_id, reflection_text, actual_success
            FROM logs
            WHERE experiment_group = 'reflection' AND reflection_text IS NOT NULL
            LIMIT 3
        """).fetchall()
        
        for r in reflections:
            status = "PASS" if r['actual_success'] else "FAIL"
            print(f"  [{r['task_id']}] {status}: {r['reflection_text'][:100]}...")

        # 3. Per-Task Breakdown
        print("\n  PER-TASK RATE COMPARISON")
        print("  " + "─"*65)
        tasks = conn.execute("""
            SELECT 
                task_id,
                experiment_group,
                AVG(actual_success) as rate
            FROM logs
            GROUP BY task_id, experiment_group
            ORDER BY task_id, experiment_group
        """).fetchall()
        
        current_task = None
        for t in tasks:
            if t['task_id'] != current_task:
                current_task = t['task_id']
                print(f"\n  {current_task:<10}", end="")
            
            print(f" | {t['experiment_group'].upper()[:4]}: {t['rate']:.0%}", end="")
        print("\n" + "═"*72 + "\n")

if __name__ == "__main__":
    analyze_p3()
