
"""Summary Dashboard Toplevel (pivot + optional chart)."""
from __future__ import annotations

import threading
from tkinter import Toplevel, BOTH, N, S, E, W
from tkinter import ttk
from tkinter import StringVar, IntVar

from .ui_config import CONFIG

try:
    import pandas as pd  # type: ignore
except Exception:  # pragma: no cover
    pd = None  # type: ignore

try:
    import matplotlib
    matplotlib.use("TkAgg")  # ensure Tk backend
    from matplotlib.figure import Figure
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg  # noqa: E402
except Exception:  # pragma: no cover
    Figure = None  # type: ignore
    FigureCanvasTkAgg = None  # type: ignore


class SummaryDashboard(Toplevel):
    def __init__(self, master, df: "pd.DataFrame | None") -> None:
        super().__init__(master)
        self.title("Summary — Config Name Counts")
        self.geometry("900x600")
        self.configure(bg=CONFIG.bg_main)

        self._df = df
        self._debounce: threading.Timer | None = None

        self._topn = IntVar(value=20)
        self._max_label = IntVar(value=40)
        self._status = StringVar(value="")

        self._build()
        self._refresh_table()
        self._refresh_chart_debounced()

    def _build(self) -> None:
        root = self
        root.grid_columnconfigure(0, weight=1)
        root.grid_rowconfigure(1, weight=1)

        bar = ttk.Frame(root)
        bar.grid(row=0, column=0, sticky=E + W, padx=8, pady=6)
        ttk.Label(bar, text="Top-N:").pack(side="left")
        ttk.Spinbox(bar, from_=1, to=1000, textvariable=self._topn, width=6, command=self._refresh_chart_debounced).pack(side="left", padx=(4, 12))
        ttk.Label(bar, text="Max label len:").pack(side="left")
        ttk.Spinbox(bar, from_=5, to=200, textvariable=self._max_label, width=6, command=self._refresh_chart_debounced).pack(side="left", padx=(4, 12))
        ttk.Button(bar, text="Export Summary CSV", command=self._export_csv).pack(side="left")
        ttk.Button(bar, text="Save Chart PNG", command=self._save_png).pack(side="left", padx=(6, 0))
        ttk.Label(bar, textvariable=self._status).pack(side="right")

        body = ttk.Panedwindow(root, orient="horizontal")
        body.grid(row=1, column=0, sticky=N + S + E + W)

        # Table
        left = ttk.Frame(body)
        left.grid_columnconfigure(0, weight=1)
        left.grid_rowconfigure(0, weight=1)
        self._tree = ttk.Treeview(left, columns=("name", "count"), show="headings")
        self._tree.heading("name", text="Config Name", command=lambda: self._sort(0))
        self._tree.heading("count", text="Count", command=lambda: self._sort(1))
        self._tree.column("name", width=300, anchor="w")
        self._tree.column("count", width=100, anchor="e")
        vsb = ttk.Scrollbar(left, orient="vertical", command=self._tree.yview)
        self._tree.configure(yscrollcommand=vsb.set)
        self._tree.grid(row=0, column=0, sticky=N + S + E + W)
        vsb.grid(row=0, column=1, sticky=N + S)

        body.add(left, weight=1)

        # Chart area
        right = ttk.Frame(body)
        right.grid_columnconfigure(0, weight=1)
        right.grid_rowconfigure(0, weight=1)
        self._chart_container = right
        body.add(right, weight=1)

    def _pivot(self):
        if pd is None or self._df is None or self._df.empty:
            return None
        candidates = [c for c in self._df.columns if str(c).lower() in {"config_name", "configname", "name", "config"}]
        col = candidates[0] if candidates else self._df.columns[0]
        pivot = (
            self._df[[col]]
            .astype(str)
            .rename(columns={col: "Config Name"})
            .assign(**{"Config Name": lambda d: d["Config Name"].str.extract(r"([A-Za-z_]+)", expand=False)})
            .dropna()
            .value_counts()
            .reset_index(name="Count")
        )
        total = int(pivot["Count"].sum())
        gt = pd.DataFrame({"Config Name": ["Grand Total"], "Count": [total]})
        pivot = pd.concat([pivot, gt], ignore_index=True)
        pivot = pivot.sort_values(["Count", "Config Name"], ascending=[False, True], kind="mergesort")
        return pivot

    def _refresh_table(self) -> None:
        self._tree.delete(*self._tree.get_children())
        pivot = self._pivot()
        if pivot is None:
            self._status.set("No data. Chart unavailable.")
            return
        for _, row in pivot.iterrows():
            tags = ("gt",) if row["Config Name"] == "Grand Total" else ()
            self._tree.insert("", "end", values=(row["Config Name"], int(row["Count"])), tags=tags)
        self._tree.tag_configure("gt", background="#e9ecef")

    def _refresh_chart_debounced(self) -> None:
        if self._debounce:
            self._debounce.cancel()
        self._debounce = threading.Timer(0.25, self._refresh_chart)
        self._debounce.start()

    def _selected_names(self) -> list[str]:
        names: list[str] = []
        for iid in self._tree.selection():
            v = self._tree.item(iid, "values")
            if v:
                names.append(str(v[0]))
        return names

    def _refresh_chart(self) -> None:
        self.after(0, self._draw_chart)

    def _draw_chart(self) -> None:
        for child in self._chart_container.winfo_children():
            child.destroy()

        if Figure is None:
            ttk.Label(self._chart_container, text="Chart unavailable. Install matplotlib for visualization.").pack(padx=12, pady=12)
            return

        pivot = self._pivot()
        if pivot is None or pivot.empty:
            ttk.Label(self._chart_container, text="No data to plot.").pack(padx=12, pady=12)
            return
        pivot = pivot[pivot["Config Name"] != "Grand Total"]

        names_selected = self._selected_names()
        if names_selected:
            data = pivot[pivot["Config Name"].isin(names_selected)]
        else:
            data = pivot.head(self._topn.get())

        max_len = self._max_label.get()
        labels = [n if len(n) <= max_len else (n[: max_len - 1] + "…") for n in data["Config Name"].tolist()]
        counts = data["Count"].tolist()

        fig = Figure(figsize=(5.5, 4.0), dpi=100)
        ax = fig.add_subplot(111)
        ax.barh(range(len(labels)), counts)
        ax.set_yticks(range(len(labels)))
        ax.set_yticklabels(labels)
        ax.invert_yaxis()
        ax.set_xlabel("Count")
        ax.set_title("Config Name Frequency")
        fig.tight_layout()

        canvas = FigureCanvasTkAgg(fig, master=self._chart_container)
        canvas.draw()
        canvas.get_tk_widget().pack(fill=BOTH, expand=True)

    def _export_csv(self) -> None:
        import tkinter.filedialog as fd

        pivot = self._pivot()
        if pivot is None or pivot.empty:
            return
        path = fd.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV", ".csv")], title="Export Summary CSV")
        if not path:
            return
        pivot.to_csv(path, index=False)
        self._status.set(f"Saved: {path}")

    def _save_png(self) -> None:
        if Figure is None:
            self._status.set("Matplotlib not installed")
            return
        import tkinter.filedialog as fd
        from matplotlib.backends.backend_agg import FigureCanvasAgg

        pivot = self._pivot()
        if pivot is None or pivot.empty:
            return
        pivot = pivot[pivot["Config Name"] != "Grand Total"]
        names_selected = self._selected_names()
        if names_selected:
            data = pivot[pivot["Config Name"].isin(names_selected)]
        else:
            data = pivot.head(self._topn.get())

        max_len = self._max_label.get()
        labels = [n if len(n) <= max_len else (n[: max_len - 1] + "…") for n in data["Config Name"].tolist()]
        counts = data["Count"].tolist()

        fig = Figure(figsize=(6, 4), dpi=120)
        ax = fig.add_subplot(111)
        ax.barh(range(len(labels)), counts)
        ax.set_yticks(range(len(labels)))
        ax.set_yticklabels(labels)
        ax.invert_yaxis()
        ax.set_xlabel("Count")
        ax.set_title("Config Name Frequency")
        fig.tight_layout()

        path = fd.asksaveasfilename(defaultextension=".png", filetypes=[("PNG", ".png")], title="Save Chart PNG")
        if not path:
            return
        canvas = FigureCanvasAgg(fig)
        canvas.draw()
        fig.savefig(path)
        self._status.set(f"Saved chart: {path}")

    def _sort(self, col_index: int) -> None:
        items = [(self._tree.set(iid, col_index), iid) for iid in self._tree.get_children("")]
        if col_index == 1:
            items.sort(key=lambda x: int(x[0]) if str(x[0]).isdigit() else 0, reverse=True)
        else:
            items.sort(key=lambda x: str(x[0]).lower())
        for idx, (_, iid) in enumerate(items):
            self._tree.move(iid, "", idx)
