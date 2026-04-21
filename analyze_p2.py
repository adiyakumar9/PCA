"""
analyze_p2.py — Analyze results of Phase 2 A/B Testing.
Compares 'control' vs 'belief' group performance.
"""

from db import get_connection

def analyze_p2():
    with get_connection() as conn:
        print("\n" + "═"*64)
        print("  PHASE 2: GROUNDING VALIDATION REPORT")
        print("═"*64)
        
        # 1. Overall Comparison
        stats = conn.execute("""
            SELECT 
                experiment_group,
                COUNT(*) as runs,
                SUM(actual_success) as wins,
                AVG(actual_success) as rate
            FROM logs
            WHERE experiment_group IN ('control', 'belief')
            GROUP BY experiment_group
        """).fetchall()
        
        if not stats:
            print("No Phase 2 data found in logs.")
            return

        print(f"  {'GROUP':<12} {'RUNS':<8} {'SUCCESS':<12} {'RATE':<10}")
        print("  " + "─"*50)
        
        results = {}
        for row in stats:
            results[row['experiment_group']] = row['rate']
            print(f"  {row['experiment_group'].upper():<12} {row['runs']:<8} "
                  f"{row['wins']:<12} {row['rate']:.1%}")
        
        if 'control' in results and 'belief' in results:
            delta = results['belief'] - results['control']
            print("  " + "─"*50)
            print(f"  IMPROVEMENT (Delta): {delta:+.1%}")

        # 2. Per-Task Breakdown
        print("\n  PER-TASK PERFORMANCE")
        print("  " + "─"*60)
        tasks = conn.execute("""
            SELECT 
                task_id,
                experiment_group,
                COUNT(*) as runs,
                AVG(actual_success) as rate
            FROM logs
            GROUP BY task_id, experiment_group
            ORDER BY task_id, experiment_group
        """).fetchall()
        
        print(f"  {'TASK':<10} {'GROUP':<10} {'RUNS':<8} {'RATE':<10}")
        for t in tasks:
            print(f"  {t['task_id']:<10} {t['experiment_group']:<10} "
                  f"{t['runs']:<8} {t['rate']:.1%}")
                  
        print("═"*64 + "\n")

if __name__ == "__main__":
    analyze_p2()
