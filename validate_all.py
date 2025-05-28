import os
import subprocess

def run_simulation_and_compare(sim_dir, out_dir):
    simulation_files = [f for f in os.listdir(sim_dir) if f.endswith('.json')]
    total = len(simulation_files)
    passed = 0
    report_lines = []

    for sim_file in simulation_files:
        base_name = sim_file.replace('.json', '')
        sim_path = os.path.join(sim_dir, sim_file)
        expected_output_path = os.path.join(out_dir, base_name + '.txt')

        try:
            subprocess.run(
                ['python', 'simulator.py', sim_path, 'temp_log.txt'],
                check=True
            )
        except subprocess.CalledProcessError as e:
            line = f"[FAIL] {base_name} crashed during execution"
            print(line)
            report_lines.append(line + "\n" + str(e) + "\n")
            continue

        # Read actual simulator output
        if os.path.exists('temp_log.txt'):
            with open('temp_log.txt', 'r') as log_file:
                actual_output = log_file.read().strip()
        else:
            actual_output = ""

        # Read expected output
        with open(expected_output_path, 'r') as f:
            expected_output = f.read().strip()

        # Compare outputs
        if actual_output == expected_output:
            line = f"[PASS] {base_name}"
            passed += 1
        else:
            line = f"[FAIL] {base_name}"
            print(line)
            report_lines.append(line)
            report_lines.append("---- Expected ----")
            report_lines.append(expected_output)
            report_lines.append("---- Actual ----")
            report_lines.append(actual_output)
            report_lines.append("------------------")

        print(line)

        # Clean up
        if os.path.exists('temp_log.txt'):
            os.remove('temp_log.txt')

    summary = f"\nPassed {passed}/{total} tests"
    print(summary)
    report_lines.append(summary)

    with open("summary_report.txt", "w", encoding="utf-8") as summary_file:
        summary_file.write("\n".join(report_lines))

if __name__ == '__main__':
    run_simulation_and_compare('simulations', 'correct_output')
