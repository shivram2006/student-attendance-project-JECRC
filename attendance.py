"""
Classroom Attendance Heatmap & Chart
===================================
A clean, modular Python practical script for tracking student attendance,
calculating eligibility records, and generating visual heatmaps and charts.

Core Tasks:
- Task 1: Load CSV, validate columns, standardize status, extract student roster.
- Task 2: Interactive CLI menu to either process stored data or mark today's attendance.
- Task 3: Calculate attendance summary, eligibility status (75% threshold), low-attendance alerts, and export CSV.
- Task 4: Generate Attendance Heatmap (Seaborn) and Percentage Bar Chart (Matplotlib).
"""

import os
from datetime import datetime, date
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import seaborn as sns


# ==============================================================================
# CONFIGURATION & CONSTANTS
# ==============================================================================
DATA_DIR = "data"
OUTPUT_DIR = "outputs"
CSV_FILE_PATH = os.path.join(DATA_DIR, "attendance.csv")
SUMMARY_CSV_PATH = os.path.join(OUTPUT_DIR, "attendance_summary.csv")
HEATMAP_IMG_PATH = os.path.join(OUTPUT_DIR, "attendance_heatmap.png")
CHART_IMG_PATH = os.path.join(OUTPUT_DIR, "attendance_chart.png")

REQUIRED_COLUMNS = ["student_id", "student_name", "date", "status"]
ATTENDANCE_THRESHOLD = 75.0  # Percentage required for eligibility


# ==============================================================================
# INITIALIZATION / SAMPLE DATA GENERATION
# ==============================================================================
def ensure_sample_data(csv_path: str = CSV_FILE_PATH) -> None:
    """
    Ensures that the attendance CSV file exists. If missing, creates the
    data/ directory and populates it with realistic sample attendance records
    (10 students across 10 lecture dates = 100 rows) with varying attendance rates.
    """
    if os.path.exists(csv_path):
        return

    os.makedirs(os.path.dirname(csv_path), exist_ok=True)
    print(f"[INFO] '{csv_path}' not found. Generating realistic sample dataset (~100 rows)...")

    # 10 Students with unique IDs
    students = [
        ("S101", "Aarav Sharma"),
        ("S102", "Ananya Patel"),
        ("S103", "Rohan Gupta"),
        ("S104", "Sneha Reddy"),
        ("S105", "Vikram Singh"),
        ("S106", "Priya Nair"),
        ("S107", "Ishaan Verma"),
        ("S108", "Diya Mukherjee"),
        ("S109", "Kabir Mehta"),
        ("S110", "Tanvi Joshi"),
    ]

    # 10 Consecutive working days (YYYY-MM-DD)
    dates = [
        "2026-11-02", "2026-11-03", "2026-11-04", "2026-11-05", "2026-11-06",
        "2026-11-09", "2026-11-10", "2026-11-11", "2026-11-12", "2026-11-13"
    ]

    # Realistic attendance patterns:
    # High attendance: S101 (100%), S104 (90%), S105 (90%), S110 (100%)
    # Moderate attendance (Eligible): S102 (80%), S106 (80%)
    # Borderline/Shortage: S103 (70%), S107 (60%), S108 (50%), S109 (40%)
    attendance_patterns = {
        "S101": [1, 1, 1, 1, 1, 1, 1, 1, 1, 1],  # 10/10 = 100%
        "S102": [1, 1, 0, 1, 1, 1, 1, 0, 1, 1],  # 8/10  = 80%
        "S103": [1, 0, 1, 1, 0, 1, 1, 0, 1, 1],  # 7/10  = 70% (Shortage)
        "S104": [1, 1, 1, 1, 1, 0, 1, 1, 1, 1],  # 9/10  = 90%
        "S105": [1, 1, 1, 0, 1, 1, 1, 1, 1, 1],  # 9/10  = 90%
        "S106": [0, 1, 1, 1, 1, 1, 1, 1, 0, 1],  # 8/10  = 80%
        "S107": [1, 0, 1, 0, 1, 1, 0, 1, 0, 1],  # 6/10  = 60% (Shortage)
        "S108": [1, 0, 0, 1, 0, 1, 0, 1, 1, 0],  # 5/10  = 50% (Shortage)
        "S109": [0, 1, 0, 0, 1, 0, 1, 0, 0, 1],  # 4/10  = 40% (Shortage)
        "S110": [1, 1, 1, 1, 1, 1, 1, 1, 1, 1],  # 10/10 = 100%
    }

    records = []
    for s_id, s_name in students:
        pattern = attendance_patterns[s_id]
        for day, status in zip(dates, pattern):
            records.append({
                "student_id": s_id,
                "student_name": s_name,
                "date": day,
                "status": status
            })

    sample_df = pd.DataFrame(records)
    sample_df.to_csv(csv_path, index=False)
    print(f"[SUCCESS] Created '{csv_path}' with {len(sample_df)} sample attendance records.\n")


# ==============================================================================
# TASK 1: LOAD, VALIDATE & EXTRACT STUDENT ROSTER
# ==============================================================================
def load_and_validate_attendance(csv_path: str = CSV_FILE_PATH) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Loads attendance data from CSV, validates required columns, standardizes
    status to integers (1 or 0), sorts chronological records, and extracts
    the unique student roster.

    Returns:
        tuple[pd.DataFrame, pd.DataFrame]: (cleaned_attendance_df, student_roster_df)
    """
    ensure_sample_data(csv_path)

    df = pd.read_csv(csv_path)

    # Validate required columns
    missing_cols = [col for col in REQUIRED_COLUMNS if col not in df.columns]
    if missing_cols:
        raise ValueError(
            f"CSV is missing required column(s): {missing_cols}. "
            f"Expected columns: {REQUIRED_COLUMNS}"
        )

    # Clean & standardize types
    df["student_id"] = df["student_id"].astype(str).str.strip()
    df["student_name"] = df["student_name"].astype(str).str.strip()
    df["date"] = pd.to_datetime(df["date"]).dt.strftime("%Y-%m-%d")

    # Standardize status to 0 or 1
    # Accepts 1/0, True/False, '1'/'0', 'P'/'A', 'Present'/'Absent'
    def standardize_status(val):
        if pd.isna(val):
            return 0
        s = str(val).strip().upper()
        if s in ["1", "TRUE", "P", "PRESENT"]:
            return 1
        elif s in ["0", "FALSE", "A", "ABSENT"]:
            return 0
        else:
            try:
                num = int(float(s))
                return 1 if num > 0 else 0
            except ValueError:
                return 0

    df["status"] = df["status"].apply(standardize_status)

    # Sort records chronologically and by student ID
    df = df.sort_values(by=["date", "student_id"]).reset_index(drop=True)

    # Extract unique student roster
    roster = (
        df[["student_id", "student_name"]]
        .drop_duplicates()
        .sort_values(by="student_id")
        .reset_index(drop=True)
    )

    return df, roster


def print_student_roster(roster: pd.DataFrame) -> None:
    """Prints the unique student roster in a clean table format."""
    print("=" * 45)
    print("            OFFICIAL STUDENT ROSTER          ")
    print("=" * 45)
    print(f"{'No.':<5} {'Student ID':<15} {'Student Name':<25}")
    print("-" * 45)
    for idx, row in roster.iterrows():
        print(f"{idx + 1:<5} {row['student_id']:<15} {row['student_name']:<25}")
    print("=" * 45)
    print(f"Total Enrolled Students: {len(roster)}\n")


# ==============================================================================
# TASK 2: DAILY ATTENDANCE MARKING (CLI INPUT & STORAGE)
# ==============================================================================
def mark_daily_attendance(df: pd.DataFrame, roster: pd.DataFrame, csv_path: str = CSV_FILE_PATH) -> pd.DataFrame:
    """
    Prompts the user to mark attendance for today (or a chosen date) for each
    student in the roster. Appends the new entries to the CSV file and returns
    the updated DataFrame.
    """
    print("\n" + "=" * 50)
    print("        DAILY ATTENDANCE ENTRY MODULE         ")
    print("=" * 50)

    # Determine attendance date
    today_str = date.today().strftime("%Y-%m-%d")
    date_input = input(f"Enter attendance date (YYYY-MM-DD) [Default: Today ({today_str})]: ").strip()
    target_date = date_input if date_input else today_str

    # Validate date format
    try:
        datetime.strptime(target_date, "%Y-%m-%d")
    except ValueError:
        print("[ERROR] Invalid date format. Please use YYYY-MM-DD. Aborting entry.")
        return df

    # Check if attendance is already recorded for this date
    existing_dates = df["date"].unique()
    if target_date in existing_dates:
        print(f"\n[WARNING] Attendance records already exist for {target_date}!")
        overwrite_choice = input("Do you wish to overwrite/append attendance for this date? (y/n): ").strip().lower()
        if overwrite_choice != 'y':
            print("[INFO] Attendance marking cancelled.")
            return df
        # If continuing, remove previous entries for this date to avoid duplicate student rows
        df = df[df["date"] != target_date].copy()

    print(f"\nMarking attendance for Date: {target_date}")
    print("Instructions: Enter '1' for Present, '0' for Absent (or 'P' / 'A').")
    print("-" * 50)

    new_records = []
    for idx, row in roster.iterrows():
        s_id = row["student_id"]
        s_name = row["student_name"]

        while True:
            prompt = f"[{idx + 1}/{len(roster)}] {s_id} - {s_name} (1=Present, 0=Absent): "
            user_entry = input(prompt).strip().upper()

            if user_entry in ["1", "P", "PRESENT"]:
                status = 1
                break
            elif user_entry in ["0", "A", "ABSENT"]:
                status = 0
                break
            else:
                print("  -> Invalid input. Please enter 1 (Present) or 0 (Absent).")

        new_records.append({
            "student_id": s_id,
            "student_name": s_name,
            "date": target_date,
            "status": status
        })

    # Combine new records with existing records
    new_df = pd.DataFrame(new_records)
    updated_df = pd.concat([df, new_df], ignore_index=True)
    updated_df = updated_df.sort_values(by=["date", "student_id"]).reset_index(drop=True)

    # Save to CSV
    updated_df.to_csv(csv_path, index=False)
    print(f"\n[SUCCESS] Successfully recorded {len(new_records)} attendance entries for {target_date}.")
    print(f"[INFO] Updated master dataset written to: '{csv_path}'\n")

    return updated_df


# ==============================================================================
# TASK 3: ATTENDANCE PERCENTAGE CALCULATION & EXPORT
# ==============================================================================
def calculate_attendance_summary(df: pd.DataFrame, output_path: str = SUMMARY_CSV_PATH) -> pd.DataFrame:
    """
    Computes aggregated attendance metrics per student:
      - attended: Total classes attended (status == 1)
      - total_classes: Total distinct class sessions conducted
      - attendance_pct: (attended / total_classes) * 100
      - status: 'Eligible' if attendance_pct >= 75.0% else 'Shortage'

    Prints a formatted summary table and low-attendance alerts to the terminal,
    and exports the summary table to a CSV file.
    """
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    # Calculate total class sessions in the dataset
    total_distinct_classes = df["date"].nunique()

    # Group by student
    summary = (
        df.groupby(["student_id", "student_name"], as_index=False)
        .agg(
            attended=("status", "sum"),
            total_classes=("date", "nunique")
        )
    )

    # Note: total_classes for each student matches their tracked sessions
    # Compute attendance percentage and eligibility status
    summary["attendance_pct"] = (summary["attended"] / summary["total_classes"]) * 100
    summary["attendance_pct"] = summary["attendance_pct"].round(2)
    summary["status"] = summary["attendance_pct"].apply(
        lambda pct: "Eligible" if pct >= ATTENDANCE_THRESHOLD else "Shortage"
    )

    # Sort descending by attendance percentage for clear presentation
    summary = summary.sort_values(by=["attendance_pct", "student_id"], ascending=[False, True]).reset_index(drop=True)

    # Print Formatted Table in Terminal
    print("=" * 75)
    print("               CLASSROOM ATTENDANCE SUMMARY RECORD               ")
    print(f"       Total Class Sessions Conducted: {total_distinct_classes} | Minimum Required: {ATTENDANCE_THRESHOLD}%")
    print("=" * 75)
    header = f"{'ID':<8} {'Student Name':<20} {'Attended':<10} {'Total':<8} {'Percent':<12} {'Eligibility'}"
    print(header)
    print("-" * 75)
    for _, row in summary.iterrows():
        pct_str = f"{row['attendance_pct']:.2f}%"
        status_flag = "[OK] Eligible" if row["status"] == "Eligible" else "[!] SHORTAGE"
        print(f"{row['student_id']:<8} {row['student_name']:<20} {int(row['attended']):<10} {int(row['total_classes']):<8} {pct_str:<12} {status_flag}")
    print("=" * 75)

    # Low-attendance Alerts
    shortage_students = summary[summary["status"] == "Shortage"]
    print("\n" + "!" * 75)
    print(f"  ATTENDANCE SHORTAGE ALERT (< {ATTENDANCE_THRESHOLD}%)  —  Action Required!")
    print("!" * 75)
    if not shortage_students.empty:
        for _, row in shortage_students.iterrows():
            print(f"  * [ALERT] {row['student_name']} ({row['student_id']}): "
                  f"{row['attended']}/{row['total_classes']} classes attended ({row['attendance_pct']:.2f}%)")
    else:
        print("  * Excellent! All students meet or exceed the 75% attendance threshold.")
    print("!" * 75 + "\n")

    # Export summary table to CSV
    summary.to_csv(output_path, index=False)
    print(f"[EXPORT] Summary report saved to: '{output_path}'")

    return summary


# ==============================================================================
# TASK 4: PLOT HEATMAP & SUMMARY BAR CHART
# ==============================================================================
def generate_visualizations(
    df: pd.DataFrame,
    summary_df: pd.DataFrame,
    heatmap_path: str = HEATMAP_IMG_PATH,
    chart_path: str = CHART_IMG_PATH
) -> None:
    """
    Generates and saves two high-quality visual outputs:
      1. Attendance Heatmap (Seaborn): Student vs. Date matrix showing daily attendance.
      2. Attendance Percentage Bar Chart (Matplotlib): Student attendance percentage
         with threshold line at 75% and color coding for shortage alerts.
    """
    os.makedirs(os.path.dirname(heatmap_path), exist_ok=True)
    os.makedirs(os.path.dirname(chart_path), exist_ok=True)

    # --------------------------------------------------------------------------
    # Subtask 4A: Attendance Heatmap
    # --------------------------------------------------------------------------
    print("[INFO] Generating Attendance Heatmap...")

    # Pivot dataset: index = student_name, columns = date, values = status
    heatmap_matrix = df.pivot(index="student_name", columns="date", values="status")
    heatmap_matrix = heatmap_matrix.fillna(0).astype(int)

    # Sort students alphabetically for a clean display
    heatmap_matrix = heatmap_matrix.sort_index(ascending=True)

    plt.figure(figsize=(12, 6.5))

    # Binary colormap: 0 = Absent (Soft Coral Red), 1 = Present (Teal / Emerald Green)
    cmap = mcolors.ListedColormap(["#f87171", "#34d399"])

    ax = sns.heatmap(
        heatmap_matrix,
        cmap=cmap,
        annot=True,
        fmt="d",
        linewidths=1.2,
        linecolor="#f1f5f9",
        cbar_kws={
            "ticks": [0.25, 0.75],
            "label": "Attendance Status",
            "shrink": 0.6
        }
    )

    # Customize colorbar tick labels
    cbar = ax.collections[0].colorbar
    cbar.ax.set_yticklabels(["Absent (0)", "Present (1)"])

    plt.title("Classroom Attendance Heatmap (Daily Status)", fontsize=15, pad=18, fontweight="bold")
    plt.xlabel("Class Date (YYYY-MM-DD)", fontsize=11, labelpad=12, fontweight="bold")
    plt.ylabel("Student Name", fontsize=11, labelpad=12, fontweight="bold")
    plt.xticks(rotation=45, ha="right", fontsize=9.5)
    plt.yticks(rotation=0, fontsize=9.5)

    # Save cleanly with tight bounding box
    plt.savefig(heatmap_path, dpi=300, bbox_inches="tight")
    plt.close()
    print(f"[SUCCESS] Heatmap saved to: '{heatmap_path}'")

    # --------------------------------------------------------------------------
    # Subtask 4B: Attendance Percentage Bar Chart
    # --------------------------------------------------------------------------
    print("[INFO] Generating Attendance Percentage Chart...")

    # Sort summary by student name for orderly reading
    chart_data = summary_df.sort_values(by="student_name", ascending=True).copy()

    plt.figure(figsize=(12, 6.5))

    # Color code bars: Red for Shortage (< 75%), Emerald Green for Eligible (>= 75%)
    bar_colors = [
        "#34d399" if pct >= ATTENDANCE_THRESHOLD else "#f87171"
        for pct in chart_data["attendance_pct"]
    ]

    bars = plt.bar(
        chart_data["student_name"],
        chart_data["attendance_pct"],
        color=bar_colors,
        edgecolor="#334155",
        linewidth=0.8,
        width=0.55
    )

    # Threshold dashed line at 75%
    plt.axhline(
        y=ATTENDANCE_THRESHOLD,
        color="#dc2626",
        linestyle="--",
        linewidth=1.8,
        label=f"{ATTENDANCE_THRESHOLD}% Minimum Attendance Requirement"
    )

    # Add numeric percentage labels above each bar
    for bar in bars:
        height = bar.get_height()
        plt.text(
            bar.get_x() + bar.get_width() / 2.0,
            height + 1.2,
            f"{height:.1f}%",
            ha="center",
            va="bottom",
            fontsize=9.5,
            fontweight="bold",
            color="#1e293b"
        )

    plt.title("Student Attendance Percentage & Eligibility Chart", fontsize=15, pad=18, fontweight="bold")
    plt.xlabel("Student Name", fontsize=11, labelpad=12, fontweight="bold")
    plt.ylabel("Attendance Percentage (%)", fontsize=11, labelpad=12, fontweight="bold")
    plt.ylim(0, 115)  # Leave headroom for labels
    plt.xticks(rotation=40, ha="right", fontsize=9.5)
    plt.yticks(range(0, 101, 10), fontsize=9.5)
    plt.grid(axis="y", linestyle=":", alpha=0.6)

    # Legend for threshold and status categories
    legend_elements = [
        plt.Line2D([0], [0], color="#dc2626", linestyle="--", linewidth=1.8, label=f"Threshold ({ATTENDANCE_THRESHOLD}%)"),
        plt.Rectangle((0, 0), 1, 1, facecolor="#34d399", edgecolor="#334155", label="Eligible (>= 75%)"),
        plt.Rectangle((0, 0), 1, 1, facecolor="#f87171", edgecolor="#334155", label="Shortage (< 75%)")
    ]
    plt.legend(handles=legend_elements, loc="upper right", framealpha=0.9)

    # Save cleanly with tight bounding box
    plt.savefig(chart_path, dpi=300, bbox_inches="tight")
    plt.close()
    print(f"[SUCCESS] Attendance chart saved to: '{chart_path}'")


# ==============================================================================
# MAIN WORKFLOW & INTERACTIVE MENU
# ==============================================================================
def run_pipeline(df: pd.DataFrame, roster: pd.DataFrame) -> None:
    """Executes Task 1 (display), Task 3 (summary), and Task 4 (visualizations)."""
    # Print Roster
    print_student_roster(roster)

    # Task 3: Calculate attendance percentage & export summary CSV
    summary_df = calculate_attendance_summary(df, SUMMARY_CSV_PATH)

    # Task 4: Generate Heatmap and Bar Chart
    generate_visualizations(df, summary_df, HEATMAP_IMG_PATH, CHART_IMG_PATH)

    # Final output locations
    print("\n" + "=" * 65)
    print("             ALL TASKS COMPLETED SUCCESSFULLY            ")
    print("=" * 65)
    print(f"1. Master Attendance CSV : {os.path.abspath(CSV_FILE_PATH)}")
    print(f"2. Attendance Summary CSV: {os.path.abspath(SUMMARY_CSV_PATH)}")
    print(f"3. Attendance Heatmap    : {os.path.abspath(HEATMAP_IMG_PATH)}")
    print(f"4. Attendance Bar Chart  : {os.path.abspath(CHART_IMG_PATH)}")
    print("=" * 65 + "\n")


def main() -> None:
    """Entry point: Displays startup menu and guides user through options."""
    print("\n" + "#" * 65)
    print("   CLASSROOM ATTENDANCE HEATMAP & CHART SYSTEM")
    print("   Practical Project — Attendance Analytics & Visualizations")
    print("#" * 65 + "\n")

    # Task 1: Load and validate attendance data
    df, roster = load_and_validate_attendance(CSV_FILE_PATH)

    # Task 2: Startup Menu
    print("Please select an operation mode:")
    print("  [1] Generate report & charts from existing CSV data")
    print("  [2] Mark today's daily attendance (CLI input) & generate updated report")
    print("  [3] Exit")

    choice = input("\nEnter choice (1, 2, or 3) [Default: 1]: ").strip()

    if choice == "2":
        # Mark daily attendance, append to CSV, reload data
        df = mark_daily_attendance(df, roster, CSV_FILE_PATH)
        # Re-extract roster and run pipeline
        df, roster = load_and_validate_attendance(CSV_FILE_PATH)
        run_pipeline(df, roster)
    elif choice == "3":
        print("\nExiting. Have a great day!")
    else:
        # Default or choice == "1"
        if choice not in ["", "1"]:
            print(f"[NOTE] Unrecognized option '{choice}'. Defaulting to option 1.")
        run_pipeline(df, roster)


if __name__ == "__main__":
    main()
