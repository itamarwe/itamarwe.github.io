"""
Manim scene for the post "Semantic Context That Builds Itself":
how the context layer builds itself, bottom to top.

    manim -qh --format=mp4 anim.py Process

This is a schematic on a handful of made-up tables, not a recording of the real
system. It shows the order of operations (physical discovery -> usage mining ->
lineage -> agent discovery + human curation) and the asymmetry of learning; the
numbers on screen are illustrative. No LaTeX: every label is Text.
"""
from manim import *

BG, LIGHT, MUTED, DIM = "#000000", "#ededed", "#8b95a5", "#2a3140"
CYAN, GOLD, GREEN, RED, PURPLE = "#3fc1ff", "#ffd166", "#7CFC8A", "#ff5a5a", "#b48cff"
config.background_color = BG
MONO = "Menlo"
SANS = "Helvetica Neue"
Text.set_default(font=SANS)


def table_box(name, pos, color=DIM, w=2.0, h=0.62):
    box = RoundedRectangle(width=w, height=h, corner_radius=0.08, stroke_color=color,
                           stroke_width=2, fill_color="#0b0f15", fill_opacity=1)
    lab = Text(name, font=MONO, font_size=18, color=LIGHT)
    g = VGroup(box, lab).move_to(pos)
    return g


class Process(Scene):
    def construct(self):
        title = Text("How the context layer builds itself", font_size=30,
                     color=LIGHT).to_edge(UP, buff=0.35)
        self.play(FadeIn(title))

        stage = Text("", font_size=22, color=CYAN).to_corner(DL, buff=0.4)

        def set_stage(txt, color):
            new = Text(txt, font_size=22, color=color).to_corner(DL, buff=0.4)
            return Transform(stage, new)

        # ---------------- 1. physical structure ----------------------------
        self.play(set_stage("1 · physical structure — profile and sketch every table",
                            CYAN))
        names = ["customers", "orders", "events_v1", "events_v2", "transfers",
                 "products", "wallets", "sessions"]
        # laid out so that no two candidate edges cross
        positions = {
            "customers": LEFT * 4.2 + UP * 1.4, "orders": LEFT * 1.4 + UP * 1.4,
            "products": RIGHT * 1.4 + UP * 1.4, "sessions": RIGHT * 4.2 + UP * 1.4,
            "events_v1": LEFT * 4.2 + DOWN * 0.6, "wallets": LEFT * 1.4 + DOWN * 0.6,
            "transfers": RIGHT * 1.4 + DOWN * 0.6, "events_v2": RIGHT * 4.2 + DOWN * 0.6,
        }
        tables = {n: table_box(n, positions[n]) for n in names}
        self.play(LaggedStart(*[FadeIn(tables[n], scale=0.8) for n in names],
                              lag_ratio=0.12), run_time=1.6)

        # containment probes: sample dots fly between two tables, edge snaps in
        def probe(a, b, ratio, keep=True):
            pa, pb = tables[a].get_center(), tables[b].get_center()
            dots = VGroup(*[Dot(pa + (pb - pa) * 0.15 + UP * 0.05 * (i % 3 - 1),
                                radius=0.045, color=CYAN) for i in range(6)])
            self.play(FadeIn(dots), run_time=0.2)
            self.play(dots.animate.shift((pb - pa) * 0.7), run_time=0.6)
            col = CYAN if keep else RED
            edge = DashedLine(pa, pb, color=col, stroke_width=3, dash_length=0.12)
            d = pb - pa
            off = UP * 0.22 if abs(d[0]) > abs(d[1]) else RIGHT * 0.42
            lab = Text(f"{ratio:.2f}", font=MONO, font_size=16, color=col
                       ).move_to((pa + pb) / 2 + off)
            self.play(FadeOut(dots), Create(edge), FadeIn(lab), run_time=0.5)
            if not keep:
                self.play(FadeOut(edge), FadeOut(lab), run_time=0.4)
                return None
            return VGroup(edge, lab)

        edges = {}
        edges["cust-ord"] = probe("customers", "orders", 0.97)
        edges["cust-ev1"] = probe("customers", "events_v1", 0.94)
        edges["ord-ev2"] = probe("orders", "events_v2", 0.91)
        edges["cust-wal"] = probe("customers", "wallets", 0.89)
        edges["wal-tr"] = probe("wallets", "transfers", 0.88)
        probe("products", "sessions", 0.03, keep=False)
        edges["ord-prod"] = probe("orders", "products", 0.99)
        edges["ev2-ses"] = probe("events_v2", "sessions", 0.62)
        note = Text("candidate joins, from containment", font_size=18, color=CYAN
                    ).to_corner(DR, buff=0.4)
        self.play(FadeIn(note))
        self.wait(0.8)

        # ---------------- 2. usage ---------------------------------------
        self.play(set_stage("2 · usage — read the query logs", GOLD),
                  FadeOut(note))
        queries = [
            ("SELECT … FROM orders o JOIN customers c ON …", ["cust-ord"]),
            ("SELECT … FROM orders o JOIN products p ON …", ["ord-prod"]),
            ("SELECT … FROM transfers t JOIN wallets w ON …", ["wal-tr"]),
            ("SELECT … FROM customers c JOIN wallets w ON …", ["cust-wal"]),
            ("SELECT … FROM orders o JOIN customers c ON …", ["cust-ord"]),
            ("SELECT … FROM orders o JOIN events_v2 e ON …", ["ord-ev2"]),
            ("SELECT … FROM orders o JOIN products p ON …", ["ord-prod"]),
            ("SELECT … FROM transfers t JOIN wallets w ON …", ["wal-tr"]),
        ]
        widths = {k: 3 for k in edges}
        for q, used in queries:
            line = Text(q, font=MONO, font_size=14, color=MUTED).move_to(DOWN * 2.2 + LEFT * 7)
            self.add(line)
            anims = [line.animate.shift(RIGHT * 14).set_opacity(0)]
            for k in used:
                widths[k] += 2.2
                e = edges[k][0]
                anims.append(e.animate.set_stroke(color=GOLD, width=widths[k]))
            self.play(*anims, run_time=0.55, rate_func=linear)
            self.remove(line)
        # unused candidates fade
        self.play(*[edges[k].animate.set_opacity(0.3) for k in ["cust-ev1", "ev2-ses"]],
                  run_time=0.6)
        note = Text("used joins thicken · unused ones fade", font_size=18, color=GOLD
                    ).to_corner(DR, buff=0.4)
        self.play(FadeIn(note))
        self.wait(0.6)

        # lineage: a derived table appears
        self.play(set_stage("2 · usage — lineage falls out of the logs", GOLD),
                  FadeOut(note))
        ctas = Text("CREATE TABLE settlement_daily AS SELECT … FROM transfers JOIN wallets …",
                    font=MONO, font_size=13, color=MUTED).move_to(DOWN * 2.2)
        self.play(FadeIn(ctas), run_time=0.5)
        derived = table_box("settlement_daily", RIGHT * 3.6 + DOWN * 2.55, color=GOLD, w=2.7)
        l1 = Arrow(tables["transfers"].get_bottom(), derived.get_top(), color=GOLD,
                   stroke_width=2.5, buff=0.08, max_tip_length_to_length_ratio=0.12)
        l2 = Arrow(tables["wallets"].get_bottom(), derived.get_top(), color=GOLD,
                   stroke_width=2.5, buff=0.08, max_tip_length_to_length_ratio=0.12)
        self.play(FadeOut(ctas), FadeIn(derived), Create(l1), Create(l2), run_time=0.9)
        note = Text("DERIVED_FROM edges, feeds the finance dashboard", font_size=18,
                    color=GOLD).to_corner(DR, buff=0.4)
        self.play(FadeIn(note))
        self.wait(0.8)

        # ---------------- 3. discovery + curation --------------------------
        self.play(set_stage("3 · curation — an agent discovers, a human decides", PURPLE),
                  FadeOut(note))
        agent = Text("agent", font_size=20, color=GREEN).move_to(LEFT * 5.4 + DOWN * 2.6)
        abox = SurroundingRectangle(agent, color=GREEN, buff=0.15, corner_radius=0.08)
        self.play(FadeIn(agent), Create(abox))
        # the agent tries customers <-> events_v1 (a faded candidate) and it fails
        e = edges["cust-ev1"]
        q = Text("JOIN events_v1 e ON e.customer_id = c.id  →  0 rows", font=MONO,
                 font_size=13, color=RED).next_to(abox, RIGHT, buff=0.3)
        self.play(FadeIn(q), e.animate.set_opacity(1).set_stroke(color=RED, width=4),
                  run_time=0.6)
        self.wait(0.5)
        finding = Text("found: lowercase ids on one side, mixed-case on the other",
                       font=MONO, font_size=13, color=GREEN).next_to(abox, RIGHT, buff=0.3)
        self.play(Transform(q, finding), run_time=0.6)
        self.wait(0.6)
        prop = Text("proposed: normalize case before joining", font_size=16, color=GREEN
                    ).next_to(e[1], RIGHT, buff=0.15)
        self.play(FadeIn(prop), e.animate.set_stroke(color=GREEN, width=3), run_time=0.6)

        # a human promotes
        human = Text("analyst", font_size=20, color=PURPLE).move_to(LEFT * 5.4 + DOWN * 2.6)
        hbox = SurroundingRectangle(human, color=PURPLE, buff=0.15, corner_radius=0.08)
        self.play(FadeOut(q), Transform(agent, human), Transform(abox, hbox), run_time=0.5)
        ok = Text("approved ✓", font_size=16, color=PURPLE).next_to(e[1], RIGHT, buff=0.15)
        self.play(FadeOut(prop), FadeIn(ok), e[0].animate.set_stroke(color=PURPLE, width=4),
                  run_time=0.6)
        # a human deprecates events_v1 after a date
        say = Text("“don't use events_v1 after Jan 2026, use events_v2”", font_size=16,
                   color=PURPLE).next_to(abox, RIGHT, buff=0.3)
        self.play(FadeIn(say), run_time=0.5)
        strike = Line(tables["events_v1"].get_left(), tables["events_v1"].get_right(),
                      color=RED, stroke_width=3)
        dep = Text("deprecated after 2026-01", font_size=14, color=RED).next_to(
            tables["events_v1"], DOWN, buff=0.08)
        self.play(Create(strike), FadeIn(dep), run_time=0.6)
        self.wait(1.0)

        # ---------------- pedestal ---------------------------------------
        self.play(*[FadeOut(m) for m in self.mobjects if m not in (title,)], run_time=0.8)
        tiers = VGroup()
        specs = [("physical structure", CYAN, 8.0), ("usage", GOLD, 5.8),
                 ("curation", PURPLE, 3.6)]
        y = -2.2
        for name, col, w in specs:
            box = RoundedRectangle(width=w, height=1.1, corner_radius=0.1, stroke_color=col,
                                   stroke_width=3, fill_color=col, fill_opacity=0.12
                                   ).move_to(UP * y)
            lab = Text(name, font_size=26, color=col).move_to(box)
            tiers.add(VGroup(box, lab))
            y += 1.25
        self.play(LaggedStart(*[FadeIn(t, shift=UP * 0.3) for t in tiers], lag_ratio=0.35),
                  run_time=1.6)
        tagline = Text("derive what you can · learn what you can · ask for what remains",
                       font_size=22, color=MUTED).next_to(tiers, UP, buff=0.5)
        self.play(FadeIn(tagline))
        self.wait(2.0)
