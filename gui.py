import os
import threading
import tkinter as tk
from tkinter import filedialog, scrolledtext, messagebox
import soundfile as sf

# ── Try importing heavy deps so we can show friendly errors ─────────────────
try:
    import sounddevice as sd
    SD_OK = True
except ImportError:
    SD_OK = False

try:
    from voxcpm import VoxCPM
    VOXCPM_OK = True
except ImportError:
    VOXCPM_OK = False

# ── Folders ──────────────────────────────────────────────────────────────────
OUTPUT_FOLDER = "outputs"
VOICE_FOLDER  = "voice_samples"
os.makedirs(OUTPUT_FOLDER, exist_ok=True)
os.makedirs(VOICE_FOLDER,  exist_ok=True)

# ── Defaults (exactly as in your original script) ────────────────────────────
DEFAULT_PROMPT = (
    "(Bass-baritone. Glacially slow. Each word lands alone, then fades. "
    "Long silences between thoughts — never filled, never rushed. Breath is deep, "
    "infrequent, almost imperceptible. No warmth. No urgency. Just weight. "
    "The voice carries age, distance, and quiet inevitability. Speak as if the "
    "universe itself is in no hurry. Every sentence ends in stillness.)"
)

DEFAULT_SCRIPT = (
    "Every year, thousands of people go missing... And not all of them are found. "
    "A child. A parent. A friend. In those first critical hours, every second matters. "
    "But information is scattered. Delayed. Sometimes lost. "
    "What if there was a way to change that? "
    "Introducing MyTRACE. A smarter, faster way to connect communities and bring the missing home. "
    "Because finding one person... can mean saving an entire world."
)

DEFAULT_CFG   = 1.6
DEFAULT_STEPS = 40

# ── Palette ───────────────────────────────────────────────────────────────────
C = {
    "bg":       "#0B0F14",
    "panel":    "#13181F",
    "border":   "#1E2732",
    "text":     "#D9E1EC",
    "muted":    "#6B7A8F",
    "amber":    "#E8A020",
    "amber2":   "#B87810",
    "green":    "#2EA84A",
    "red":      "#D64040",
    "mono":     ("Courier New", 10),
    "ui":       ("Segoe UI", 10),
    "ui_sm":    ("Segoe UI", 9),
    "ui_bold":  ("Segoe UI", 10, "bold"),
    "label":    ("Segoe UI", 8, "bold"),
}


# ╔═══════════════════════════════════════════════════════════════════════════╗
# ║  Helpers                                                                  ║
# ╚═══════════════════════════════════════════════════════════════════════════╝
def make_panel(parent, **kw):
    f = tk.Frame(parent, bg=C["panel"],
                 highlightbackground=C["border"], highlightthickness=1, **kw)
    return f

def label(parent, text, style="label", fg=None, **kw):
    return tk.Label(parent,
                    text=text,
                    font=C[style],
                    fg=fg or (C["amber"] if style == "label" else C["text"]),
                    bg=parent["bg"],
                    **kw)

def text_area(parent, height, default=""):
    t = scrolledtext.ScrolledText(
        parent, height=height, font=C["mono"], wrap="word",
        bg="#0B0F14", fg=C["text"], insertbackground=C["amber"],
        relief="flat", padx=10, pady=8, highlightthickness=0,
        selectbackground=C["amber"], selectforeground=C["bg"])
    t.insert("1.0", default)
    return t

def amber_btn(parent, text, cmd, width=None):
    kw = dict(width=width) if width else {}
    b = tk.Button(parent, text=text, command=cmd,
                  font=C["ui_bold"], bg=C["amber"], fg=C["bg"],
                  activebackground=C["amber2"], activeforeground=C["bg"],
                  relief="flat", padx=16, pady=8, cursor="hand2",
                  bd=0, **kw)
    b.bind("<Enter>", lambda e: b.config(bg=C["amber2"]))
    b.bind("<Leave>", lambda e: b.config(bg=C["amber"] if b["state"] == "normal" else C["border"]))
    return b

def ghost_btn(parent, text, cmd, width=None):
    kw = dict(width=width) if width else {}
    b = tk.Button(parent, text=text, command=cmd,
                  font=C["ui"], bg=C["panel"], fg=C["text"],
                  activebackground=C["border"], activeforeground=C["text"],
                  relief="flat", padx=12, pady=7, cursor="hand2",
                  bd=0, highlightbackground=C["border"], highlightthickness=1,
                  **kw)
    return b


# ╔═══════════════════════════════════════════════════════════════════════════╗
# ║  App                                                                      ║
# ╚═══════════════════════════════════════════════════════════════════════════╝
class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("MyTRACE · Voice Studio")
        self.configure(bg=C["bg"])
        self.minsize(900, 680)

        self.model   = None
        self.busy    = False
        self.last_wav = None
        self.last_sr  = None
        self.voice_files: list[str] = []

        self._header()
        self._body()
        self._footer()

    # ── Header ────────────────────────────────────────────────────────────
    def _header(self):
        h = tk.Frame(self, bg=C["panel"],
                     highlightbackground=C["border"], highlightthickness=1,
                     height=52)
        h.pack(fill="x")
        h.pack_propagate(False)

        tk.Label(h, text="●", fg=C["amber"], bg=C["panel"],
                 font=("Segoe UI", 20)).pack(side="left", padx=(16, 4))
        tk.Label(h, text="Developed for MyTRACE by Mandol", fg=C["text"], bg=C["panel"],
                 font=("Segoe UI", 14, "bold")).pack(side="left")
        tk.Label(h, text="Voice Studio", fg=C["muted"], bg=C["panel"],
                 font=("Segoe UI", 10)).pack(side="left", padx=(8, 0))

        self._badge = tk.Label(h, text="  MODEL NOT LOADED  ",
            fg="white", bg=C["red"],
            font=("Segoe UI", 8, "bold"), padx=8, pady=3)
        self._badge.pack(side="right", padx=16, pady=10)

        help_btn = tk.Button(h, text="?  Help", command=self._show_help,
                             font=("Segoe UI", 9, "bold"),
                             bg=C["border"], fg=C["text"],
                             activebackground=C["muted"], activeforeground=C["bg"],
                             relief="flat", padx=12, pady=4, cursor="hand2", bd=0)
        help_btn.pack(side="right", padx=(0, 8), pady=10)
        help_btn.bind("<Enter>", lambda e: help_btn.config(bg=C["muted"], fg=C["bg"]))
        help_btn.bind("<Leave>", lambda e: help_btn.config(bg=C["border"], fg=C["text"]))

    # ── Help popup ────────────────────────────────────────────────────────
    def _show_help(self):
        win = tk.Toplevel(self)
        win.title("Help — MyTRACE Voice Studio")
        win.configure(bg=C["bg"])
        win.resizable(False, False)
        win.grab_set()  # modal

        # Centre over main window
        self.update_idletasks()
        x = self.winfo_x() + (self.winfo_width()  - 560) // 2
        y = self.winfo_y() + (self.winfo_height() - 600) // 2
        win.geometry(f"560x600+{x}+{y}")

        # Header strip
        hdr = tk.Frame(win, bg=C["panel"],
                       highlightbackground=C["border"], highlightthickness=1,
                       height=46)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)
        tk.Label(hdr, text="?", fg=C["amber"], bg=C["panel"],
                 font=("Segoe UI", 18, "bold")).pack(side="left", padx=(16, 6))
        tk.Label(hdr, text="How to use MyTRACE Voice Studio",
                 fg=C["text"], bg=C["panel"],
                 font=("Segoe UI", 11, "bold")).pack(side="left", pady=10)

        # Scrollable content
        canvas = tk.Canvas(win, bg=C["bg"], highlightthickness=0)
        sb = tk.Scrollbar(win, orient="vertical", command=canvas.yview,
                          bg=C["border"], troughcolor=C["panel"])
        canvas.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y", padx=(0, 4), pady=8)
        canvas.pack(fill="both", expand=True, padx=12, pady=8)

        content = tk.Frame(canvas, bg=C["bg"])
        canvas_win = canvas.create_window((0, 0), window=content, anchor="nw")

        def _on_resize(e):
            canvas.itemconfig(canvas_win, width=e.width)
        canvas.bind("<Configure>", _on_resize)
        content.bind("<Configure>",
                     lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.bind_all("<MouseWheel>",
                        lambda e: canvas.yview_scroll(-1*(e.delta//120), "units"))

        # ── Content sections ──────────────────────────────────────────────
        sections = [
            ("STEP 1 — Load the Model", C["amber"],
             "Click  ⬇ Load Model  on the right panel.\n\n"
             "• Model ID:  leave as  openbmb/VoxCPM2  (downloads automatically on first run, ~4–8 GB).\n"
             "• Load denoiser:  leave unchecked unless you have 10 GB+ VRAM. It slightly improves quality but uses a lot more memory.\n"
             "• The badge in the top-right changes from red to green when the model is ready.\n\n"
             "⚠  Requires PyTorch ≥ 2.5.  If you see a 'scaled_dot_product_attention' error, run:\n"
             "   pip install \"torch>=2.5.0\" --upgrade"),

            ("STEP 2 — Set the Voice Style Prompt", C["amber"],
             "This tells the model how the voice should sound.\n\n"
             "Write a plain-English description in parentheses, for example:\n"
             "  (Warm female voice. Conversational pace. Slight British accent.)\n\n"
             "Tips:\n"
             "• Describe tone, speed, accent, age, emotion.\n"
             "• More specific = more consistent results.\n"
             "• You can leave it blank to use the model's default voice."),

            ("STEP 3 — Write the Script", C["amber"],
             "Type or paste the text you want spoken into the Voice Script box.\n\n"
             "Tips:\n"
             "• Use  ...  (ellipsis) to add natural pauses.\n"
             "• Short sentences tend to sound more natural than very long ones.\n"
             "• The prompt and script are combined before being sent to the model."),

            ("STEP 4 — Adjust Parameters", C["amber"],
             "CFG Value  (default 1.6)\n"
             "  Controls how closely the model follows your voice prompt.\n"
             "  • Lower (1.0–1.4) = more natural, less strict.\n"
             "  • Higher (1.8–2.5) = more faithful to the prompt, can sound stiffer.\n\n"
             "Inference Steps  (default 40)\n"
             "  More steps = slower but often higher quality audio.\n"
             "  • Fast preview: 20 steps.\n"
             "  • Best quality: 50–80 steps.\n\n"
             "Output Filename\n"
             "  The .wav file is saved to the  outputs/  folder next to this script."),

            ("STEP 5 — Generate & Listen", C["amber"],
             "Click  ▶ GENERATE  and wait (typically 10–60 seconds depending on your GPU/CPU).\n\n"
             "Once done:\n"
             "• ⏵ Play  — listens to the result immediately (requires sounddevice).\n"
             "• 💾 Save As…  — export a copy anywhere on your computer.\n"
             "• The auto-saved file is always in the  outputs/  folder."),

            ("VOICE CLONING  (optional)", C["muted"],
             "Upload your own .wav recordings to guide the voice style.\n\n"
             "• Click  + Add .wav  and select one or more recordings of the target voice.\n"
             "• Recordings should be clean, 5–30 seconds, minimal background noise.\n"
             "• Note: this feature requires a model version that includes a speaker encoder. "
             "The base VoxCPM2 model may not support it."),

            ("TROUBLESHOOTING", C["muted"],
             "scaled_dot_product_attention error\n"
             "  → pip install \"torch>=2.5.0\" --upgrade\n\n"
             "CUDA out of memory\n"
             "  → Uncheck 'Load denoiser', reduce Inference Steps to 20.\n\n"
             "No sound on Play\n"
             "  → pip install sounddevice\n"
             "     On Linux also: sudo apt install libportaudio2\n\n"
             "Model download is slow\n"
             "  → It only downloads once. Cached in  ~/.cache/huggingface/"),
        ]

        for title, title_color, body_text in sections:
            # Section title
            tk.Label(content, text=title,
                     font=("Segoe UI", 9, "bold"), fg=title_color,
                     bg=C["bg"], anchor="w").pack(fill="x", pady=(14, 2), padx=4)
            # Divider
            tk.Frame(content, bg=C["border"], height=1).pack(fill="x", padx=4)
            # Body
            tk.Label(content, text=body_text,
                     font=("Segoe UI", 9), fg=C["text"],
                     bg=C["panel"], justify="left", anchor="nw",
                     wraplength=500, padx=12, pady=10).pack(
                         fill="x", padx=4, pady=(0, 2))

        # Close button
        tk.Frame(win, bg=C["border"], height=1).pack(fill="x", padx=12)
        amber_btn(win, "Close", win.destroy).pack(pady=12)

    # ── Body ──────────────────────────────────────────────────────────────
    def _body(self):
        body = tk.Frame(self, bg=C["bg"])
        body.pack(fill="both", expand=True, padx=16, pady=14)
        body.columnconfigure(0, weight=3)
        body.columnconfigure(1, weight=2)
        body.rowconfigure(0, weight=1)

        left = tk.Frame(body, bg=C["bg"])
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        right = tk.Frame(body, bg=C["bg"])
        right.grid(row=0, column=1, sticky="nsew")

        self._left(left)
        self._right(right)

    def _section(self, parent, title, expand=False):
        """Labelled panel. Returns the inner frame."""
        wrap = tk.Frame(parent, bg=C["bg"])
        wrap.pack(fill="x" if not expand else "both",
                  expand=expand, pady=(0, 10))
        tk.Label(wrap, text=title, font=C["label"], fg=C["amber"],
                 bg=C["bg"]).pack(anchor="w", pady=(0, 4))
        inner = make_panel(wrap)
        inner.pack(fill="both", expand=expand)
        return inner

    # ── Left column ───────────────────────────────────────────────────────
    def _left(self, parent):
        # Voice prompt
        s1 = self._section(parent, "VOICE STYLE PROMPT")
        self.prompt_box = text_area(s1, 5, DEFAULT_PROMPT)
        self.prompt_box.pack(fill="x", padx=1, pady=1)

        # Script
        s2 = self._section(parent, "VOICE SCRIPT", expand=True)
        self.script_box = text_area(s2, 8, DEFAULT_SCRIPT)
        self.script_box.pack(fill="both", expand=True, padx=1, pady=1)

        # Parameters
        s3 = self._section(parent, "GENERATION PARAMETERS")
        row = tk.Frame(s3, bg=C["panel"])
        row.pack(fill="x", padx=12, pady=10)

        # CFG
        tk.Label(row, text="CFG Value", font=C["ui_sm"], fg=C["muted"],
                 bg=C["panel"]).grid(row=0, column=0, sticky="w")
        self.cfg_var = tk.StringVar(value=str(DEFAULT_CFG))
        tk.Spinbox(row, from_=0.1, to=10.0, increment=0.1,
                   textvariable=self.cfg_var, width=9,
                   font=C["ui"], bg=C["bg"], fg=C["text"],
                   buttonbackground=C["border"], relief="flat",
                   insertbackground=C["amber"]).grid(
                       row=1, column=0, sticky="w", padx=(0, 24), pady=(2, 0))

        # Steps
        tk.Label(row, text="Inference Steps", font=C["ui_sm"], fg=C["muted"],
                 bg=C["panel"]).grid(row=0, column=1, sticky="w")
        self.steps_var = tk.StringVar(value=str(DEFAULT_STEPS))
        tk.Spinbox(row, from_=1, to=200, increment=5,
                   textvariable=self.steps_var, width=9,
                   font=C["ui"], bg=C["bg"], fg=C["text"],
                   buttonbackground=C["border"], relief="flat",
                   insertbackground=C["amber"]).grid(
                       row=1, column=1, sticky="w", padx=(0, 24), pady=(2, 0))

        # Filename
        tk.Label(row, text="Output Filename", font=C["ui_sm"], fg=C["muted"],
                 bg=C["panel"]).grid(row=0, column=2, sticky="w")
        self.fname_var = tk.StringVar(value="mytrace_intro.wav")
        tk.Entry(row, textvariable=self.fname_var, width=18,
                 font=C["ui"], bg=C["bg"], fg=C["text"],
                 insertbackground=C["amber"], relief="flat").grid(
                     row=1, column=2, sticky="w", pady=(2, 0))

        # Buttons
        brow = tk.Frame(parent, bg=C["bg"])
        brow.pack(fill="x", pady=(2, 0))

        self.gen_btn  = amber_btn(brow, "▶  GENERATE", self._generate)
        self.gen_btn.pack(side="left", padx=(0, 8))

        self.play_btn = ghost_btn(brow, "⏵  Play", self._play)
        self.play_btn.pack(side="left", padx=(0, 6))
        self.play_btn.config(state="disabled")

        self.save_btn = ghost_btn(brow, "💾  Save As…", self._save_as)
        self.save_btn.pack(side="left")
        self.save_btn.config(state="disabled")

        # Progress bar (manual canvas)
        self._prog_frame = tk.Frame(parent, bg=C["border"], height=3)
        self._prog_frame.pack(fill="x", pady=(10, 0))
        self._prog_bar = tk.Frame(self._prog_frame, bg=C["amber"], height=3)
        self._prog_bar.place(x=0, y=0, relwidth=0, relheight=1)
        self._prog_anim = False

    # ── Right column ──────────────────────────────────────────────────────
    def _right(self, parent):
        # Model loader
        sm = self._section(parent, "MODEL")
        mf = tk.Frame(sm, bg=C["panel"])
        mf.pack(fill="x", padx=12, pady=10)

        tk.Label(mf, text="HuggingFace model ID", font=C["ui_sm"],
                 fg=C["muted"], bg=C["panel"]).pack(anchor="w")
        self.model_id = tk.StringVar(value="openbmb/VoxCPM2")
        tk.Entry(mf, textvariable=self.model_id, font=C["ui"],
                 bg=C["bg"], fg=C["text"], insertbackground=C["amber"],
                 relief="flat").pack(fill="x", pady=(3, 8))

        self.denoiser_var = tk.BooleanVar(value=False)
        tk.Checkbutton(mf, text="Load denoiser  (more VRAM, higher quality)",
                       variable=self.denoiser_var,
                       font=C["ui_sm"], fg=C["muted"], bg=C["panel"],
                       selectcolor=C["bg"], activebackground=C["panel"],
                       activeforeground=C["muted"]).pack(anchor="w", pady=(0, 8))

        self.load_btn = amber_btn(mf, "⬇  Load Model", self._load_model)
        self.load_btn.pack(fill="x")

        # Voice cloning
        sv = self._section(parent, "VOICE CLONING  (optional)", expand=True)
        vf = tk.Frame(sv, bg=C["panel"])
        vf.pack(fill="both", expand=True, padx=12, pady=10)

        # Enable toggle
        self.clone_enabled = tk.BooleanVar(value=False)
        def _toggle_clone():
            s = "normal" if self.clone_enabled.get() else "disabled"
            self.wav_list.config(state=s)
            for w in self._clone_widgets:
                try: w.config(state=s)
                except: pass
            self._update_active_label()
        tk.Checkbutton(vf, text="Enable voice cloning",
                       variable=self.clone_enabled, command=_toggle_clone,
                       font=C["ui_sm"], fg=C["text"], bg=C["panel"],
                       selectcolor=C["bg"], activebackground=C["panel"],
                       activeforeground=C["text"]).pack(anchor="w", pady=(0, 6))

        tk.Label(vf,
                 text="Select ONE .wav reference (5-30 sec, clean audio).",
                 font=C["ui_sm"], fg=C["muted"], bg=C["panel"],
                 wraplength=240, justify="left").pack(anchor="w", pady=(0, 6))

        self.wav_list = tk.Listbox(
            vf, bg=C["bg"], fg=C["text"],
            selectbackground=C["amber"], selectforeground=C["bg"],
            font=C["mono"], height=5, relief="flat",
            borderwidth=0, highlightthickness=0,
            state="disabled", selectmode="single")
        self.wav_list.pack(fill="both", expand=True, pady=(0, 8))
        self.wav_list.bind("<<ListboxSelect>>", lambda e: self._update_active_label())

        br = tk.Frame(vf, bg=C["panel"])
        br.pack(fill="x")
        add_b = ghost_btn(br, "+ Add .wav", self._add_wavs)
        add_b.pack(side="left", padx=(0, 6))
        add_b.config(state="disabled")
        rem_b = ghost_btn(br, "X Remove", self._remove_wav)
        rem_b.pack(side="left")
        rem_b.config(state="disabled")
        self._clone_widgets = [add_b, rem_b]

        self._active_lbl_var = tk.StringVar(value="No reference selected.")
        tk.Label(vf, textvariable=self._active_lbl_var,
                 font=("Segoe UI", 8), fg=C["amber"], bg=C["panel"],
                 anchor="w").pack(anchor="w", pady=(8, 0))

    # ── Footer / log ──────────────────────────────────────────────────────
    def _footer(self):
        f = tk.Frame(self, bg=C["panel"],
                     highlightbackground=C["border"], highlightthickness=1,
                     height=30)
        f.pack(fill="x", padx=16, pady=(0, 12))
        f.pack_propagate(False)
        tk.Label(f, text="LOG", font=("Segoe UI", 8, "bold"),
                 fg=C["muted"], bg=C["panel"]).pack(side="left", padx=10)
        self._log_var = tk.StringVar(value="Ready.")
        tk.Label(f, textvariable=self._log_var,
                 font=C["mono"], fg=C["text"], bg=C["panel"],
                 anchor="w").pack(side="left", fill="x", expand=True)

    def _log(self, msg):
        self._log_var.set(msg)

    # ── Progress animation ────────────────────────────────────────────────
    def _start_progress(self):
        self._prog_anim = True
        self._prog_pos  = 0.0
        self._prog_dir  = 1
        self._animate_progress()

    def _animate_progress(self):
        if not self._prog_anim:
            return
        self._prog_pos += 0.015 * self._prog_dir
        if self._prog_pos >= 0.85:
            self._prog_dir = -1
        if self._prog_pos <= 0.0:
            self._prog_dir = 1
        self._prog_bar.place(relwidth=self._prog_pos)
        self.after(30, self._animate_progress)

    def _stop_progress(self):
        self._prog_anim = False
        self._prog_bar.place(relwidth=0)

    # ── Load model ────────────────────────────────────────────────────────
    def _load_model(self):
        if not VOXCPM_OK:
            messagebox.showerror("Missing package",
                "voxcpm is not installed.\n\nRun:\n  pip install voxcpm")
            return
        if self.busy:
            return
        self.busy = True
        self.load_btn.config(state="disabled")
        self._start_progress()
        self._log("Loading model… this may take a minute.")
        threading.Thread(target=self._load_worker, daemon=True).start()

    def _load_worker(self):
        try:
            m = VoxCPM.from_pretrained(
                self.model_id.get().strip(),
                load_denoiser=self.denoiser_var.get())
            self.after(0, self._on_loaded, m, None)
        except Exception as e:
            self.after(0, self._on_loaded, None, str(e))

    def _on_loaded(self, m, err):
        self.busy = False
        self._stop_progress()
        self.load_btn.config(state="normal")
        if err:
            self._log(f"ERROR: {err}")
            messagebox.showerror("Load failed", err)
        else:
            self.model = m
            self._badge.config(text="  MODEL READY  ", bg=C["green"])
            self._log("Model loaded. Ready to generate.")

    # ── Generate ──────────────────────────────────────────────────────────
    def _generate(self):
        if self.model is None:
            messagebox.showwarning("No model", "Please load the model first.")
            return
        if self.busy:
            return
        self.busy = True
        self.gen_btn.config(state="disabled")
        self.play_btn.config(state="disabled")
        self.save_btn.config(state="disabled")
        self._start_progress()
        self._log("Generating… please wait.")
        threading.Thread(target=self._gen_worker, daemon=True).start()

    def _gen_worker(self):
        try:
            prompt = self.prompt_box.get("1.0", "end").strip()
            script = self.script_box.get("1.0", "end").strip()
            text   = f"{prompt}\n{script}" if prompt else script

            cfg   = float(self.cfg_var.get())
            steps = int(self.steps_var.get())

            # ── Voice cloning: pass reference_wav_path if enabled ────────
            ref_path = None
            if self.clone_enabled.get() and self.voice_files:
                sel = self.wav_list.curselection()
                idx = sel[0] if sel else 0
                ref_path = self.voice_files[idx]

            gen_kwargs = dict(text=text, cfg_value=cfg, inference_timesteps=steps)
            if ref_path:
                gen_kwargs["reference_wav_path"] = ref_path
                self.after(0, self._log, f"Cloning voice from: {os.path.basename(ref_path)}")

            wav = self.model.generate(**gen_kwargs)

            sr = self.model.tts_model.sample_rate
            fname = self.fname_var.get().strip() or "output.wav"
            if not fname.endswith(".wav"):
                fname += ".wav"
            out_path = os.path.join(OUTPUT_FOLDER, fname)
            sf.write(out_path, wav, sr)

            self.last_wav = wav
            self.last_sr  = sr
            self.after(0, self._on_generated, None, out_path)
        except Exception as e:
            self.after(0, self._on_generated, str(e), None)

    def _on_generated(self, err, path):
        self.busy = False
        self._stop_progress()
        self.gen_btn.config(state="normal")
        if err:
            self._log(f"ERROR: {err}")
            messagebox.showerror("Generation failed", err)
        else:
            self.play_btn.config(state="normal")
            self.save_btn.config(state="normal")
            self._log(f"Done ✓  →  {path}")

    # ── Play ──────────────────────────────────────────────────────────────
    def _play(self):
        if self.last_wav is None:
            return
        if not SD_OK:
            messagebox.showwarning("Missing package",
                "sounddevice not installed.\n\nRun:\n  pip install sounddevice")
            return
        def _do():
            sd.play(self.last_wav, self.last_sr)
            sd.wait()
        threading.Thread(target=_do, daemon=True).start()
        self._log("Playing…")

    # ── Save As ───────────────────────────────────────────────────────────
    def _save_as(self):
        if self.last_wav is None:
            return
        path = filedialog.asksaveasfilename(
            defaultextension=".wav",
            filetypes=[("WAV audio", "*.wav"), ("All files", "*.*")],
            initialfile=self.fname_var.get())
        if path:
            sf.write(path, self.last_wav, self.last_sr)
            self._log(f"Exported → {path}")

    # ── Voice files ───────────────────────────────────────────────────────
    def _update_active_label(self):
        if not self.clone_enabled.get() or not self.voice_files:
            self._active_lbl_var.set("No reference selected.")
            return
        sel = self.wav_list.curselection()
        if sel:
            self._active_lbl_var.set(f"Active: {os.path.basename(self.voice_files[sel[0]])}")
        else:
            self._active_lbl_var.set(f"{len(self.voice_files)} file(s) loaded — click one to select.")

    def _add_wavs(self):
        paths = filedialog.askopenfilenames(
            title="Select .wav voice reference",
            filetypes=[("WAV audio", "*.wav"), ("All files", "*.*")])
        for p in paths:
            if p not in self.voice_files:
                self.voice_files.append(p)
                self.wav_list.insert("end", os.path.basename(p))
        if paths:
            # Auto-select the first added file
            if self.wav_list.size() > 0:
                self.wav_list.selection_clear(0, "end")
                self.wav_list.selection_set(len(self.voice_files) - len(paths))
            self._update_active_label()
            self._log(f"Added {len(paths)} voice file(s).")

    def _remove_wav(self):
        for i in reversed(self.wav_list.curselection()):
            self.voice_files.pop(i)
            self.wav_list.delete(i)
        self._update_active_label()


if __name__ == "__main__":
    App().mainloop()