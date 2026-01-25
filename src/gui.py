import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import threading
import queue
from src import cleaner_core

class CleanerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("DS_Store & AppleDouble Cleaner")
        self.root.geometry("800x600")

        # Variables
        self.drive_vars = {} # map path -> BooleanVar
        self.log_queue = queue.Queue()

        # UI Layout
        self.create_widgets()

        # Start looking for drives
        self.refresh_drives()

        # Start log consumer
        self.process_logs()

    def create_widgets(self):
        # Top Frame: Drives
        self.top_frame = ttk.LabelFrame(self.root, text="Detected External Drives")
        self.top_frame.pack(fill="x", padx=10, pady=5)

        self.drive_list_frame = ttk.Frame(self.top_frame)
        self.drive_list_frame.pack(fill="x", padx=5, pady=5)

        self.refresh_btn = ttk.Button(self.top_frame, text="Refresh Drives", command=self.refresh_drives)
        self.refresh_btn.pack(pady=5)

        # Middle Frame: Actions
        self.action_frame = ttk.Frame(self.root)
        self.action_frame.pack(fill="x", padx=10, pady=5)

        self.preview_btn = ttk.Button(self.action_frame, text="Preview Scan (Dry Run)", command=lambda: self.start_scan(dry_run=True))
        self.preview_btn.pack(side="left", padx=5)

        self.clean_btn = ttk.Button(self.action_frame, text="Clean Selected Drives", command=lambda: self.start_scan(dry_run=False))
        self.clean_btn.pack(side="left", padx=5)

        # Bottom Frame: Logs
        self.log_frame = ttk.LabelFrame(self.root, text="Logs & Found Files")
        self.log_frame.pack(fill="both", expand=True, padx=10, pady=5)

        self.log_text = scrolledtext.ScrolledText(self.log_frame, state='disabled')
        self.log_text.pack(fill="both", expand=True, padx=5, pady=5)

        # Status Bar
        self.status_var = tk.StringVar()
        self.status_var.set("Ready")
        self.status_bar = ttk.Label(self.root, textvariable=self.status_var, relief="sunken", anchor="w")
        self.status_bar.pack(fill="x")

    def log(self, message):
        self.log_queue.put(message)

    def process_logs(self):
        while not self.log_queue.empty():
            msg = self.log_queue.get()
            self.log_text.configure(state='normal')
            self.log_text.insert("end", msg + "\n")
            self.log_text.see("end")
            self.log_text.configure(state='disabled')
        self.root.after(100, self.process_logs)

    def refresh_drives(self):
        # Clear existing checkboxes
        for widget in self.drive_list_frame.winfo_children():
            widget.destroy()
        self.drive_vars.clear()

        volumes = cleaner_core.get_external_volumes()

        if not volumes:
            lbl = ttk.Label(self.drive_list_frame, text="No external drives found.")
            lbl.pack()
        else:
            for vol in volumes:
                var = tk.BooleanVar(value=True)
                chk = ttk.Checkbutton(self.drive_list_frame, text=vol, variable=var)
                chk.pack(anchor="w")
                self.drive_vars[vol] = var

        self.status_var.set(f"Found {len(volumes)} volumes.")

    def start_scan(self, dry_run):
        selected_drives = [vol for vol, var in self.drive_vars.items() if var.get()]

        if not selected_drives:
            messagebox.showwarning("No Drives Selected", "Please select at least one drive.")
            return

        if not dry_run:
            if not messagebox.askyesno("Confirm Clean", "Are you sure you want to delete these files? This action cannot be undone."):
                return

        # Disable buttons
        self.preview_btn.config(state="disabled")
        self.clean_btn.config(state="disabled")
        self.refresh_btn.config(state="disabled")

        # Run in thread
        thread = threading.Thread(target=self.run_cleaner, args=(selected_drives, dry_run))
        thread.start()

    def run_cleaner(self, drives, dry_run):
        total_success = 0
        total_fail = 0

        mode = "DRY RUN" if dry_run else "CLEANING"
        self.log(f"--- STARTING {mode} ---")

        for drive in drives:
            self.log(f"Scanning {drive}...")
            try:
                files_found = list(cleaner_core.scan_for_junk(drive))
                if not files_found:
                    self.log(f"No junk files found in {drive}.")
                    continue

                self.log(f"Found {len(files_found)} files in {drive}.")

                def callback(path, status):
                    self.log(f"[{status}] {path}")

                s, f = cleaner_core.clean_files(files_found, dry_run=dry_run, callback=callback)
                total_success += s
                total_fail += f

            except Exception as e:
                self.log(f"Error scanning {drive}: {e}")

        self.log(f"--- FINISHED {mode} ---")
        self.log(f"Total processed: {total_success}, Failed: {total_fail}")
        self.status_var.set(f"Finished. Success: {total_success}, Fail: {total_fail}")

        # Re-enable buttons (must be done in main thread, but tkinter is somewhat thread-safe for config, better to use after)
        self.root.after(0, self.enable_buttons)

    def enable_buttons(self):
        self.preview_btn.config(state="normal")
        self.clean_btn.config(state="normal")
        self.refresh_btn.config(state="normal")

def main():
    root = tk.Tk()
    app = CleanerApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()
