import tkinter as tk
from tkinter import ttk, messagebox, filedialog, simpledialog
from typing import Optional, List, Dict, Any

try:
    import pandas as pd
    PANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False

try:
    import matplotlib
    matplotlib.use("TkAgg") # Must be called before pyplot import
    from matplotlib.figure import Figure
    from matplotlib.backends.backend_tkagg import (
        FigureCanvasTkAgg, NavigationToolbar2Tk
    )
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False
    
from . import ui_config

class SummaryDashboard(tk.Toplevel):
    """
    A Toplevel window that displays a summary pivot table and an
    optional bar chart of diff counts by Config Name.
    """

    def __init__(
        self, 
        parent: tk.Tk, 
        df: "pd.DataFrame", 
        config_name_col: str
    ):
        """
        Initializes the Summary Dashboard.

        Args:
            parent: The parent tk.Tk window.
            df: The *full* pandas DataFrame from the file loader.
            config_name_col: The column name to group by for the pivot.
        """
        super().__init__(parent)
        self.title("Diff Summary by Config Name")
        self.geometry(ui_config.DEFAULT_SUMMARY_GEOMETRY)
        
        # Per requirements, do not set iconphoto() if matplotlib is used
        # to avoid Tk pixmap errors.
        if not MATPLOTLIB_AVAILABLE:
            try:
                # Set icon only if matplotlib is NOT involved
                self.iconbitmap(default=None) # Or path to an .ico
            except tk.TclError:
                pass # Ignore if it fails

        self.df = df
        self.config_name_col = config_name_col
        self.pivot_df: Optional[pd.DataFrame] = None
        
        self.protocol("WM_DELETE_WINDOW", self.destroy)
        
        self._build_ui()
        self._generate_pivot_data()
        self._populate_table()
        self._debounced_redraw_chart = None
        self._schedule_chart_redraw() # Initial chart render

    def _build_ui(self) -> None:
        """Constructs the UI components."""
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)
        
        # Main paned window (Table | Chart)
        main_pane = ttk.PanedWindow(self, orient=tk.HORIZONTAL)
        main_pane.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        
        # --- Left Side: Table ---
        table_frame = ttk.Frame(main_pane, padding=5)
        table_frame.grid_rowconfigure(0, weight=1)
        table_frame.grid_columnconfigure(0, weight=1)
        
        cols = ("Config Name", "Count")
        self.tree = ttk.Treeview(table_frame, columns=cols, show="headings")
        self.tree.grid(row=0, column=0, sticky="nsew")
        
        # Scrollbar
        vsb = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        vsb.grid(row=0, column=1, sticky="ns")
        self.tree.configure(yscrollcommand=vsb.set)
        
        # Headers and sorting
        for col in cols:
            self.tree.heading(
                col, 
                text=col, 
                command=lambda c=col: self._sort_table(c, False)
            )
            self.tree.column(col, width=150, stretch=True)
        self.tree.column("Config Name", width=200)
        self.tree.column("Count", width=80, stretch=False, anchor="e")
        
        # Bind selection to chart update
        self.tree.bind("<<TreeviewSelect>>", self._on_table_selection_changed)
        
        main_pane.add(table_frame, weight=1)

        # --- Right Side: Chart ---
        chart_frame = ttk.Frame(main_pane, padding=5)
        chart_frame.grid_rowconfigure(1, weight=1)
        chart_frame.grid_columnconfigure(0, weight=1)
        
        # Chart controls
        controls_frame = ttk.Frame(chart_frame)
        controls_frame.grid(row=0, column=0, sticky="ew", pady=(0, 5))
        
        ttk.Label(controls_frame, text="Top N:").pack(side=tk.LEFT, padx=(0, 5))
        self.top_n_var = tk.StringVar(value="15")
        self.top_n_spinbox = ttk.Spinbox(
            controls_frame, 
            from_=1, to=100, 
            textvariable=self.top_n_var, 
            width=5
        )
        self.top_n_spinbox.pack(side=tk.LEFT, padx=5)
        self.top_n_spinbox.bind("<KeyRelease>", self._schedule_chart_redraw)
        self.top_n_spinbox.bind("<<SpinboxSelected>>", self._schedule_chart_redraw) # tk 8.6+
        
        ttk.Label(controls_frame, text="Max Label:").pack(side=tk.LEFT, padx=(10, 5))
        self.max_label_var = tk.StringVar(value="30")
        self.max_label_spinbox = ttk.Spinbox(
            controls_frame,
            from_=5, to=100, 
            textvariable=self.max_label_var, 
            width=5
        )
        self.max_label_spinbox.pack(side=tk.LEFT, padx=5)
        self.max_label_spinbox.bind("<KeyRelease>", self._schedule_chart_redraw)
        self.max_label_spinbox.bind("<<SpinboxSelected>>", self._schedule_chart_redraw)
        
        # Canvas for matplotlib
        self.chart_canvas_frame = ttk.Frame(chart_frame)
        self.chart_canvas_frame.grid(row=1, column=0, sticky="nsew")
        self.chart_canvas_frame.grid_rowconfigure(0, weight=1)
        self.chart_canvas_frame.grid_columnconfigure(0, weight=1)
        
        self.fig_canvas = None
        self.fig = None
        self.ax = None

        if MATPLOTLIB_AVAILABLE:
            try:
                self.fig = Figure(figsize=(5, 4), dpi=100)
                self.ax = self.fig.add_subplot(111)
                
                self.fig_canvas = FigureCanvasTkAgg(self.fig, master=self.chart_canvas_frame)
                self.fig_canvas.get_tk_widget().grid(row=0, column=0, sticky="nsew")
                
                # Add Matplotlib Toolbar
                toolbar = NavigationToolbar2Tk(self.fig_canvas, self.chart_canvas_frame, pack_toolbar=False)
                toolbar.update()
                toolbar.grid(row=1, column=0, sticky="ew")

            except Exception as e:
                print(f"Error initializing matplotlib canvas: {e}")
                MATPLOTLIB_AVAILABLE = False # Disable it
                self.fig_canvas = None
                self.fig = None
                self.ax = None
        
        if not MATPLOTLIB_AVAILABLE:
            msg_label = ttk.Label(
                self.chart_canvas_frame,
                text="Chart unavailable.\nInstall 'matplotlib' for visualization.",
                justify=tk.CENTER,
                style="Warning.TLabel"
            )
            msg_label.grid(row=0, column=0, sticky="nsew")
            ttk.Style().configure("Warning.TLabel", foreground="orange")
            # Disable controls
            self.top_n_spinbox.config(state="disabled")
            self.max_label_spinbox.config(state="disabled")

        main_pane.add(chart_frame, weight=2)
        
        # --- Bottom: Buttons ---
        button_frame = ttk.Frame(self, padding=(10, 0, 10, 10))
        button_frame.grid(row=1, column=0, sticky="ew")
        
        button_frame.grid_columnconfigure(0, weight=1) # Spacer
        
        self.export_csv_btn = ttk.Button(
            button_frame, 
            text="Export Summary CSV",
            command=self._export_csv
        )
        self.export_csv_btn.grid(row=0, column=1, padx=5)
        
        self.save_png_btn = ttk.Button(
            button_frame, 
            text="Save Chart PNG",
            command=self._save_chart
        )
        self.save_png_btn.grid(row=0, column=2, padx=5)
        
        self.close_btn = ttk.Button(button_frame, text="Close", command=self.destroy)
        self.close_btn.grid(row=0, column=3, padx=5)
        
        if not MATPLOTLIB_AVAILABLE:
            self.save_png_btn.config(state="disabled")

    def _generate_pivot_data(self) -> None:
        """
        Groups the DataFrame by Config Name and calculates counts.
        Stores the result in self.pivot_df.
        """
        if self.config_name_col not in self.df.columns:
            messagebox.showerror(
                "Error", 
                f"Config Name column '{self.config_name_col}' not found in data."
            )
            self.pivot_df = pd.DataFrame(columns=["Config Name", "Count"])
            return

        try:
            # Clean data: Only use valid names [A-Za-z_]+
            # And drop None/NaN
            valid_names = self.df[self.config_name_col].astype(str).str.match(r"^[A-Za-z_]+$")
            cleaned_df = self.df[valid_names.fillna(False)]
            
            # Create pivot
            pivot = cleaned_df.groupby(self.config_name_col).size()
            pivot = pivot.reset_index(name="Count")
            pivot = pivot.sort_values(by="Count", ascending=False)
            
            # Add Grand Total
            total_count = pivot["Count"].sum()
            total_row = pd.DataFrame(
                [{"Config Name": "Grand Total", "Count": total_count}]
            )
            
            self.pivot_df = pd.concat([pivot, total_row], ignore_index=True)

        except Exception as e:
            messagebox.showerror("Pivot Error", f"Failed to create summary pivot: {e}")
            self.pivot_df = pd.DataFrame(columns=["Config Name", "Count"])

    def _populate_table(self) -> None:
        """Fills the ttk.Treeview with data from self.pivot_df."""
        self.tree.delete(*self.tree.get_children())
        
        if self.pivot_df is None:
            return

        self.tree.tag_configure(
            "total_row", 
            background=ui_config.COLOR_SUMMARY_TOTAL_BG,
            foreground=ui_config.COLOR_SUMMARY_TOTAL_FG,
            font=ui_config.FONT_BOLD
        )

        for _, row in self.pivot_df.iterrows():
            values = (row["Config Name"], row["Count"])
            tags = ()
            if row["Config Name"] == "Grand Total":
                tags = ("total_row",)
            
            self.tree.insert("", "end", values=values, tags=tags)
            
        # Default sort: Count desc, Name asc
        self._sort_table("Count", descending=True)

    def _sort_table(self, col: str, descending: bool) -> None:
        """Sorts the treeview table by a column."""
        data = [(self.tree.set(item, col), item) for item in self.tree.get_children('')]
        
        # Handle numeric vs string sort for Count col
        if col == "Count":
            try:
                data.sort(key=lambda x: int(x[0]), reverse=descending)
            except ValueError:
                data.sort(key=lambda x: str(x[0]), reverse=descending)
        else:
            data.sort(key=lambda x: str(x[0]), reverse=descending)

        for index, (val, item) in enumerate(data):
            self.tree.move(item, '', index)

        # Update heading to show sort direction
        for c in self.tree["columns"]:
            self.tree.heading(c, text=c) # Clear old arrows
            
        arrow = ' ↓' if descending else ' ↑'
        self.tree.heading(col, text=col + arrow)
        # Toggle sort direction for next click
        self.tree.heading(col, command=lambda: self._sort_table(col, not descending))

    def _on_table_selection_changed(self, event: Any = None) -> None:
        """Triggers a chart redraw when table selection changes."""
        self._schedule_chart_redraw()

    def _schedule_chart_redraw(self, event: Any = None) -> None:
        """Debounces chart redraw calls to avoid flicker."""
        if self._debounced_redraw_chart:
            self.after_cancel(self._debounced_redraw_chart)
        
        # Debounce for 150ms
        self._debounced_redraw_chart = self.after(150, self._redraw_chart)
        
    def _get_data_for_chart(self) -> pd.DataFrame:
        """
        Gets the data to be plotted based on table selection or Top-N.
        """
        if self.pivot_df is None:
            return pd.DataFrame(columns=["Config Name", "Count"])

        selected_items = self.tree.selection()
        
        if selected_items:
            # Plot only selected rows
            selected_data = []
            for item_id in selected_items:
                values = self.tree.item(item_id, "values")
                if values and values[0] != "Grand Total":
                    selected_data.append({
                        "Config Name": values[0],
                        "Count": int(values[1])
                    })
            if not selected_data:
                # Selection might be the "Grand Total" row, treat as no selection
                pass
            else:
                return pd.DataFrame(selected_data).sort_values(by="Count", ascending=True)

        # No selection or only Grand Total selected: Plot Top-N
        try:
            top_n = int(self.top_n_var.get())
        except ValueError:
            top_n = 15
            
        # Get data, exclude Grand Total, sort by Count (desc), take top N
        plot_df = self.pivot_df[self.pivot_df["Config Name"] != "Grand Total"]
        plot_df = plot_df.nlargest(top_n, "Count")
        
        # Sort ascending for horizontal bar chart (lowest at bottom)
        return plot_df.sort_values(by="Count", ascending=True)
        
    def _redraw_chart(self) -> None:
        """Clears and redraws the matplotlib bar chart."""
        if not MATPLOTLIB_AVAILABLE or not self.ax or not self.fig_canvas:
            return
            
        self._debounced_redraw_chart = None # Clear debounce timer

        try:
            plot_df = self._get_data_for_chart()
            
            if plot_df.empty:
                self.ax.clear()
                self.ax.text(0.5, 0.5, "No data to display", 
                             horizontalalignment='center', 
                             verticalalignment='center',
                             transform=self.ax.transAxes)
                self.fig_canvas.draw()
                return

            try:
                max_label_len = int(self.max_label_var.get())
            except ValueError:
                max_label_len = 30

            # Truncate labels
            def truncate(s: str, n: int) -> str:
                return (s[:n-1] + '…') if len(s) > n else s
            
            labels = [
                truncate(name, max_label_len) 
                for name in plot_df["Config Name"]
            ]
            counts = plot_df["Count"]

            self.ax.clear()
            bars = self.ax.barh(labels, counts)
            self.ax.set_title("Diff Count by Config Name")
            self.ax.set_xlabel("Number of Diffs")
            
            # Add value labels to bars
            self.ax.bar_label(bars, padding=3, fmt='%d')
            
            # Adjust layout
            self.fig.tight_layout()
            self.fig_canvas.draw()

        except Exception as e:
            print(f"Error redrawing chart: {e}")
            self.ax.clear()
            self.ax.text(0.5, 0.5, f"Chart error: {e}", 
                         color="red", ha='center', va='center',
                         transform=self.ax.transAxes)
            self.fig_canvas.draw()

    def _export_csv(self) -> None:
        """Exports the full pivot table (with Grand Total) to CSV."""
        if self.pivot_df is None or self.pivot_df.empty:
            messagebox.showwarning("Export", "No summary data to export.")
            return

        save_path = filedialog.asksaveasfilename(
            title="Save Summary As",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
            defaultextension=".csv"
        )
        if not save_path:
            return

        try:
            # Export the full pivot DataFrame
            self.pivot_df.to_csv(save_path, index=False)
            messagebox.showinfo("Export Successful", f"Summary saved to:\n{save_path}")
        except Exception as e:
            messagebox.showerror("Export Error", f"Failed to save CSV: {e}")

    def _save_chart(self) -> None:
        """Saves the current chart view as a PNG file."""
        if not MATPLOTLIB_AVAILABLE or not self.fig:
            messagebox.showwarning("Save Chart", "Chart is not available to save.")
            return

        save_path = filedialog.asksaveasfilename(
            title="Save Chart As",
            filetypes=[("PNG files", "*.png"), ("All files", "*.*")],
            defaultextension=".png"
        )
        if not save_path:
            return

        try:
            self.fig.savefig(save_path, dpi=150, bbox_inches="tight")
            messagebox.showinfo("Save Successful", f"Chart saved to:\n{save_path}")
        except Exception as e:
            messagebox.showerror("Save Error", f"Failed to save chart: {e}")