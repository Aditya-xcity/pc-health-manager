import os
import platform
import subprocess
import threading
import tkinter as tk
from tkinter import messagebox, ttk

import psutil


class PCHealthManagerApp:
    """Desktop utility to monitor system load and manage heavy processes."""

    UPDATE_INTERVAL_SECONDS = 2

    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("PC Health Manager")
        self.root.geometry("1000x700")
        self.root.minsize(900, 620)
        self.root.configure(bg="#0b1220")

        # Color system inspired by terminal monitor UIs.
        self.colors = {
            "bg": "#0b1220",
            "panel": "#111827",
            "panel_alt": "#0f172a",
            "border": "#1f2937",
            "text": "#e5e7eb",
            "muted": "#94a3b8",
            "accent": "#22d3ee",
            "success": "#22c55e",
            "warning": "#eab308",
            "danger": "#ef4444",
        }

        self.stop_event = threading.Event()
        self.refresh_event = threading.Event()

        self.cpu_value_label = None
        self.ram_value_label = None
        self.disk_value_label = None
        self.warning_label = None
        self.suggestions_label = None
        self.process_tree = None

        self._configure_ttk_styles()
        self._build_gui()

        # Prime process CPU counters so future reads become meaningful.
        self._prime_process_cpu_counters()

        self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.monitor_thread.start()

        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    # -------------------------------
    # GUI construction
    # -------------------------------
    def _configure_ttk_styles(self) -> None:
        style = ttk.Style(self.root)
        style.theme_use("clam")

        style.configure(
            "Health.Treeview",
            background=self.colors["panel_alt"],
            foreground=self.colors["text"],
            fieldbackground=self.colors["panel_alt"],
            bordercolor=self.colors["border"],
            borderwidth=1,
            rowheight=28,
            font=("Consolas", 10),
        )
        style.map(
            "Health.Treeview",
            background=[("selected", "#164e63")],
            foreground=[("selected", "#ecfeff")],
        )

        style.configure(
            "Health.Treeview.Heading",
            background=self.colors["panel"],
            foreground=self.colors["accent"],
            bordercolor=self.colors["border"],
            relief="flat",
            font=("Segoe UI", 10, "bold"),
        )
        style.map("Health.Treeview.Heading", background=[("active", self.colors["panel"])])

        style.configure(
            "Vertical.TScrollbar",
            background=self.colors["panel"],
            troughcolor=self.colors["bg"],
            bordercolor=self.colors["border"],
            arrowcolor=self.colors["accent"],
            darkcolor=self.colors["panel"],
            lightcolor=self.colors["panel"],
        )

    def _build_gui(self) -> None:
        main_container = tk.Frame(self.root, bg=self.colors["bg"], padx=12, pady=12)
        main_container.pack(fill=tk.BOTH, expand=True)

        title_label = tk.Label(
            main_container,
            text="PC Health Manager",
            font=("Segoe UI", 22, "bold"),
            bg=self.colors["bg"],
            fg=self.colors["accent"],
        )
        title_label.pack(anchor="w", pady=(0, 10))

        # Top section: system information + current dashboard metrics.
        top_section = tk.Frame(main_container, bg=self.colors["bg"])
        top_section.pack(fill=tk.X, pady=(0, 10))

        info_frame = tk.LabelFrame(
            top_section,
            text="System Information",
            padx=10,
            pady=10,
            font=("Segoe UI", 10, "bold"),
            bg=self.colors["panel"],
            fg=self.colors["accent"],
            bd=1,
            relief=tk.SOLID,
        )
        info_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 6))

        os_name = platform.platform()
        processor_name = platform.processor() or "Unknown"
        total_ram_gb = psutil.virtual_memory().total / (1024 ** 3)

        tk.Label(
            info_frame,
            text=f"OS: {os_name}",
            font=("Segoe UI", 10),
            bg=self.colors["panel"],
            fg=self.colors["text"],
            anchor="w",
            justify="left",
            wraplength=430,
        ).pack(fill=tk.X, anchor="w")

        tk.Label(
            info_frame,
            text=f"Processor: {processor_name}",
            font=("Segoe UI", 10),
            bg=self.colors["panel"],
            fg=self.colors["text"],
            anchor="w",
            justify="left",
            wraplength=430,
        ).pack(fill=tk.X, anchor="w", pady=(4, 0))

        tk.Label(
            info_frame,
            text=f"Total RAM: {total_ram_gb:.2f} GB",
            font=("Segoe UI", 10),
            bg=self.colors["panel"],
            fg=self.colors["text"],
            anchor="w",
        ).pack(fill=tk.X, anchor="w", pady=(4, 0))

        dashboard_frame = tk.LabelFrame(
            top_section,
            text="System Health Dashboard",
            padx=10,
            pady=10,
            font=("Segoe UI", 10, "bold"),
            bg=self.colors["panel"],
            fg=self.colors["accent"],
            bd=1,
            relief=tk.SOLID,
        )
        dashboard_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(6, 0))

        self.cpu_value_label = self._create_metric_row(dashboard_frame, "CPU Usage")
        self.ram_value_label = self._create_metric_row(dashboard_frame, "RAM Usage")
        self.disk_value_label = self._create_metric_row(dashboard_frame, "Disk Usage")

        warning_frame = tk.LabelFrame(
            main_container,
            text="Smart Suggestions",
            padx=10,
            pady=10,
            font=("Segoe UI", 10, "bold"),
            bg=self.colors["panel"],
            fg=self.colors["accent"],
            bd=1,
            relief=tk.SOLID,
        )
        warning_frame.pack(fill=tk.X, pady=(0, 10))

        self.warning_label = tk.Label(
            warning_frame,
            text="System load is healthy.",
            font=("Segoe UI", 11, "bold"),
            bg=self.colors["panel"],
            fg=self.colors["success"],
            anchor="w",
            justify="left",
        )
        self.warning_label.pack(fill=tk.X)

        self.suggestions_label = tk.Label(
            warning_frame,
            text="No suggested apps to close.",
            font=("Consolas", 10),
            bg=self.colors["panel"],
            fg=self.colors["muted"],
            anchor="w",
            justify="left",
        )
        self.suggestions_label.pack(fill=tk.X, pady=(4, 0))

        process_section = tk.LabelFrame(
            main_container,
            text="Top Heavy Processes",
            padx=10,
            pady=10,
            font=("Segoe UI", 10, "bold"),
            bg=self.colors["panel"],
            fg=self.colors["accent"],
            bd=1,
            relief=tk.SOLID,
        )
        process_section.pack(fill=tk.BOTH, expand=True)

        columns = ("name", "pid", "cpu", "memory")
        self.process_tree = ttk.Treeview(
            process_section,
            columns=columns,
            show="headings",
            height=18,
            style="Health.Treeview",
        )
        self.process_tree.heading("name", text="Process Name")
        self.process_tree.heading("pid", text="PID")
        self.process_tree.heading("cpu", text="CPU Usage %")
        self.process_tree.heading("memory", text="Memory Usage (MB)")

        self.process_tree.tag_configure("healthy", foreground=self.colors["success"])
        self.process_tree.tag_configure("moderate", foreground=self.colors["warning"])
        self.process_tree.tag_configure("high", foreground=self.colors["danger"])

        self.process_tree.column("name", width=330, anchor="w")
        self.process_tree.column("pid", width=80, anchor="center")
        self.process_tree.column("cpu", width=120, anchor="center")
        self.process_tree.column("memory", width=150, anchor="center")

        scrollbar = ttk.Scrollbar(process_section, orient=tk.VERTICAL, command=self.process_tree.yview)
        self.process_tree.configure(yscroll=scrollbar.set)

        self.process_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        actions_frame = tk.Frame(main_container, bg=self.colors["bg"])
        actions_frame.pack(fill=tk.X, pady=(10, 0))

        refresh_button = tk.Button(
            actions_frame,
            text="Refresh",
            command=self.request_manual_refresh,
            bg="#0891b2",
            fg="#ecfeff",
            activebackground="#0e7490",
            activeforeground="#ecfeff",
            font=("Segoe UI", 10, "bold"),
            padx=14,
            pady=8,
            relief=tk.FLAT,
            bd=0,
        )
        refresh_button.pack(side=tk.LEFT)

        terminate_button = tk.Button(
            actions_frame,
            text="Terminate Selected Process",
            command=self.terminate_selected_process,
            bg="#b91c1c",
            fg="#fef2f2",
            activebackground="#991b1b",
            activeforeground="#fef2f2",
            font=("Segoe UI", 10, "bold"),
            padx=14,
            pady=8,
            relief=tk.FLAT,
            bd=0,
        )
        terminate_button.pack(side=tk.RIGHT)

    def _create_metric_row(self, parent: tk.Widget, metric_name: str) -> tk.Label:
        row = tk.Frame(parent, bg=self.colors["panel"])
        row.pack(fill=tk.X, pady=3)

        tk.Label(
            row,
            text=f"{metric_name}:",
            font=("Segoe UI", 11, "bold"),
            bg=self.colors["panel"],
            fg=self.colors["text"],
            width=12,
            anchor="w",
        ).pack(side=tk.LEFT)

        value_label = tk.Label(
            row,
            text="0.0%",
            font=("Segoe UI", 11, "bold"),
            bg=self.colors["panel"],
            fg=self.colors["success"],
            anchor="w",
        )
        value_label.pack(side=tk.LEFT, padx=(2, 0))
        return value_label

    # -------------------------------
    # Monitoring logic
    # -------------------------------
    def _prime_process_cpu_counters(self) -> None:
        for proc in psutil.process_iter(attrs=["pid"]):
            try:
                proc.cpu_percent(interval=None)
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue

    def _monitor_loop(self) -> None:
        while not self.stop_event.is_set():
            snapshot = self._collect_snapshot()
            self.root.after(0, self._render_snapshot, snapshot)

            if self.refresh_event.wait(timeout=self.UPDATE_INTERVAL_SECONDS):
                self.refresh_event.clear()

    def _collect_snapshot(self) -> dict:
        cpu_usage = psutil.cpu_percent(interval=0.2)
        ram_usage = psutil.virtual_memory().percent
        disk_path = os.environ.get("SystemDrive", "C:") + "\\" if os.name == "nt" else "/"
        disk_usage = psutil.disk_usage(disk_path).percent

        process_rows = []
        for proc in psutil.process_iter(attrs=["pid", "name", "memory_info"]):
            try:
                cpu_percent = proc.cpu_percent(interval=None)
                memory_mb = proc.info["memory_info"].rss / (1024 ** 2)
                process_rows.append(
                    {
                        "name": proc.info["name"] or "Unknown",
                        "pid": proc.info["pid"],
                        "cpu": float(cpu_percent),
                        "memory_mb": float(memory_mb),
                    }
                )
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess, KeyError):
                continue

        process_rows.sort(key=lambda p: p["cpu"], reverse=True)

        return {
            "cpu": cpu_usage,
            "ram": ram_usage,
            "disk": disk_usage,
            "processes": process_rows,
            "top3": process_rows[:3],
        }

    # -------------------------------
    # UI updates
    # -------------------------------
    def _render_snapshot(self, data: dict) -> None:
        cpu = data["cpu"]
        ram = data["ram"]
        disk = data["disk"]

        self._set_metric_label(self.cpu_value_label, cpu)
        self._set_metric_label(self.ram_value_label, ram)
        self._set_metric_label(self.disk_value_label, disk)

        self._update_warning_and_suggestions(cpu, ram, data["top3"])
        self._refresh_process_table(data["processes"])

    def _set_metric_label(self, label: tk.Label, value: float) -> None:
        label.config(text=f"{value:.1f}%", fg=self._status_color(value))

    @staticmethod
    def _status_color(value: float) -> str:
        if value >= 80:
            return "#ef4444"  # Red: high load
        if value >= 50:
            return "#eab308"  # Yellow: moderate load
        return "#22c55e"      # Green: healthy load

    def _update_warning_and_suggestions(self, cpu: float, ram: float, top3: list[dict]) -> None:
        if cpu > 80 or ram > 80:
            self.warning_label.config(text="High system load detected", fg=self.colors["danger"])

            if top3:
                lines = [
                    "Suggested apps to close (Top CPU consumers):",
                    *[
                        f"{index}. {proc['name']} (PID: {proc['pid']}, CPU: {proc['cpu']:.1f}%)"
                        for index, proc in enumerate(top3, start=1)
                    ],
                ]
                self.suggestions_label.config(text="\n".join(lines), fg="#fecaca")
            else:
                self.suggestions_label.config(text="No process data available.", fg="#fecaca")
        else:
            self.warning_label.config(text="System load is healthy.", fg=self.colors["success"])
            self.suggestions_label.config(text="No suggested apps to close.", fg=self.colors["muted"])

    def _refresh_process_table(self, process_rows: list[dict]) -> None:
        for item_id in self.process_tree.get_children():
            self.process_tree.delete(item_id)

        for proc in process_rows[:50]:
            if proc["cpu"] >= 80:
                tag = "high"
            elif proc["cpu"] >= 50:
                tag = "moderate"
            else:
                tag = "healthy"

            self.process_tree.insert(
                "",
                tk.END,
                values=(
                    proc["name"],
                    proc["pid"],
                    f"{proc['cpu']:.1f}",
                    f"{proc['memory_mb']:.1f}",
                ),
                tags=(tag,),
            )

    # -------------------------------
    # User actions
    # -------------------------------
    def request_manual_refresh(self) -> None:
        self.refresh_event.set()

    def terminate_selected_process(self) -> None:
        selected_items = self.process_tree.selection()
        if not selected_items:
            messagebox.showwarning("No Selection", "Please select a process to terminate.")
            return

        selected_item = selected_items[0]
        values = self.process_tree.item(selected_item, "values")
        if len(values) < 2:
            messagebox.showerror("Error", "Could not read selected process details.")
            return

        process_name = values[0]
        pid = int(values[1])

        confirm = messagebox.askyesno(
            "Confirm Termination",
            f"Are you sure you want to terminate '{process_name}' (PID: {pid})?",
        )
        if not confirm:
            return

        try:
            self._force_terminate_process(pid)
            messagebox.showinfo("Success", f"Process '{process_name}' (PID: {pid}) terminated.")
            self.request_manual_refresh()
        except Exception as exc:
            messagebox.showerror("Termination Failed", str(exc))

    def _force_terminate_process(self, pid: int) -> None:
        # Windows taskkill is robust for force termination and tree cleanup.
        if os.name == "nt":
            result = subprocess.run(
                ["taskkill", "/PID", str(pid), "/T", "/F"],
                capture_output=True,
                text=True,
                check=False,
            )
            if result.returncode != 0:
                error_text = result.stderr.strip() or result.stdout.strip() or "Unknown taskkill error"
                raise RuntimeError(error_text)
            return

        # Fallback path for non-Windows environments.
        os.kill(pid, 9)

    def _on_close(self) -> None:
        self.stop_event.set()
        self.root.destroy()


if __name__ == "__main__":
    app_root = tk.Tk()
    PCHealthManagerApp(app_root)
    app_root.mainloop()
