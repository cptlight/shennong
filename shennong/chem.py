"""Pure-Python SMILES parsing and molecular descriptors — no RDKit, no dependencies.

Why this exists: the terminal artefact of SHENNONG is a *drug candidate*, and a candidate
without a molecular structure is not a candidate.  The corpus supplies SMILES (from
PubChem, per brief §11.3); this module turns them into the descriptors a medicinal
chemist reads first: MW, logP, HBD/HBA, TPSA, ring count, rotatable bonds, and
Lipinski/Veber flags.

**Honesty about the estimators.**  Molecular weight, H-bond counts, ring count and
rotatable bonds are exact given a correct parse.  ``logP`` and ``TPSA`` are transparent
*fragment approximations*, labelled as such in every output; they are not a validated
replacement for a Crippen/Ertl implementation.  ``synthetic_accessibility`` is a crude
structural heuristic and is flagged accordingly.  A candidate's fate is decided by an
assay, not by these numbers.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass, field

# Average atomic masses (u) for elements appearing in natural products.
ATOMIC_MASS: dict[str, float] = {
    "H": 1.008, "B": 10.81, "C": 12.011, "N": 14.007, "O": 15.999,
    "F": 18.998, "P": 30.974, "S": 32.06, "Cl": 35.45, "Br": 79.904, "I": 126.904,
    "Si": 28.085, "Se": 78.971, "As": 74.922, "Hg": 200.59, "Pb": 207.2, "Na": 22.990, "K": 39.098,
}

VALENCE: dict[str, int] = {"B": 3, "C": 4, "N": 3, "O": 2, "P": 3, "S": 2, "F": 1, "Cl": 1, "Br": 1, "I": 1}

#: Ertl-style fragment contributions for TPSA (Å²).  Approximate but group-accurate for
#: the common natural-product polar groups (COOH = 20.23 + 17.07 = 37.30, correct).
_TPSA = {
    "O_hydroxyl": 20.23,
    "O_ether": 9.23,
    "O_carbonyl": 17.07,
    "N_amine0": 3.24,
    "N_amine1": 12.03,
    "N_amine2": 26.02,
    "N_aromatic": 12.89,
    "N_amide1": 29.10,
    "N_amide0": 20.31,
    "S_thioether": 25.30,
    "P": 38.80,
}

#: Heuristic fragment logP contributions (Crippen-inspired, NOT the Crippen table).
_LOGP = {
    "C_sp3": 0.45, "C_sp2": 0.30, "C_aromatic": 0.35, "C_carbonyl": 0.10,
    "O_hydroxyl": -0.90, "O_ether": -0.30, "O_carbonyl": -0.80,
    "N_amine0": -1.00, "N_amine1": -0.60, "N_amine2": -0.30, "N_aromatic": -0.50,
    "N_amide": -0.50, "S": 0.20, "P": 0.30,
    "F": 0.20, "Cl": 0.60, "Br": 0.90, "I": 1.00,
}

_ELEMENT_RE = re.compile(r"^[A-Z][a-z]?$")


@dataclass
class Atom:
    element: str
    aromatic: bool = False
    charge: int = 0
    explicit_h: int = 0
    chirality: str = ""
    bracketed: bool = False
    idx: int = 0
    bonds: list[tuple[int, float, bool]] = field(default_factory=list)  # (other, order, aromatic)


@dataclass
class Molecule:
    atoms: list[Atom]
    n_bonds: int = 0
    smiles: str = ""

    # -- graph helpers ---------------------------------------------------------------
    @property
    def heavy_atoms(self) -> list[Atom]:
        return [a for a in self.atoms if a.element != "H"]

    def degree(self, idx: int) -> int:
        return len(self.atoms[idx].bonds)

    def bond_order_sum(self, idx: int) -> float:
        return sum(order for _, order, _ in self.atoms[idx].bonds)

    def valence(self, idx: int) -> int:
        atom = self.atoms[idx]
        if atom.aromatic:
            # aromatic carbon has valence 4 (two 1.5-order bonds + one H = 4)
            return {"C": 4, "N": 3, "O": 2, "S": 2, "P": 3}.get(atom.element, VALENCE.get(atom.element, 0))
        return VALENCE.get(atom.element, 0)

    def implicit_h(self, idx: int) -> int:
        atom = self.atoms[idx]
        if atom.bracketed:
            return atom.explicit_h
        if atom.element not in VALENCE:
            return atom.explicit_h
        used = self.bond_order_sum(idx)
        if atom.aromatic:
            used = sum(1.5 if arom else order for _, order, arom in atom.bonds)
        return max(0, int(round(self.valence(idx) - used))) + atom.explicit_h

    def formula_counts(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for idx, atom in enumerate(self.atoms):
            counts[atom.element] = counts.get(atom.element, 0) + 1
            h = self.implicit_h(idx) if atom.element != "H" else 0
            if h:
                counts["H"] = counts.get("H", 0) + h
        return counts

    def is_connected(self) -> bool:
        if not self.atoms:
            return False
        seen = {0}
        stack = [0]
        while stack:
            cur = stack.pop()
            for other, _, _ in self.atoms[cur].bonds:
                if other not in seen:
                    seen.add(other)
                    stack.append(other)
        return len(seen) == len(self.atoms)


# --------------------------------------------------------------------------------------
# SMILES parsing
# --------------------------------------------------------------------------------------

_ORGANIC = {"B", "C", "N", "O", "P", "S", "F", "Cl", "Br", "I"}
_AROMATIC_LOWER = {"b", "c", "n", "o", "p", "s", "se", "as"}


def parse_smiles(smiles: str) -> Molecule:
    """Parse a SMILES string into a :class:`Molecule`.

    Supports the subset needed by natural-product structures: organic-subset atoms,
    bracket atoms with isotopes/chirality/H-count/charge, single/double/triple/aromatic
    bonds, branches, ring closures (including ``%nn``) and disconnected components.

    Raises ``ValueError`` on malformed input rather than returning a wrong molecule.
    """
    s = (smiles or "").strip()
    if not s:
        raise ValueError("empty SMILES")
    atoms: list[Atom] = []
    bonds: list[tuple[int, int, float, bool]] = []
    prev: int | None = None
    pending_order: float | None = None
    pending_aromatic = False
    branch_stack: list[int | None] = []
    ring_open: dict[str, tuple[int, float | None, bool]] = {}
    i, n = 0, len(s)

    while i < n:
        ch = s[i]
        if ch == "(":
            branch_stack.append(prev)
            i += 1
            continue
        if ch == ")":
            if not branch_stack:
                raise ValueError("unbalanced ')' in SMILES")
            prev = branch_stack.pop()
            i += 1
            continue
        if ch == ".":
            prev = None
            i += 1
            continue
        if ch in "-=#:\\/":
            if ch == "-":
                pending_order, pending_aromatic = 1.0, False
            elif ch == "=":
                pending_order, pending_aromatic = 2.0, False
            elif ch == "#":
                pending_order, pending_aromatic = 3.0, False
            elif ch == ":":
                pending_order, pending_aromatic = 1.5, True
            else:
                pending_order, pending_aromatic = 1.0, False
            i += 1
            continue
        if ch.isdigit() or ch == "%":
            if ch == "%":
                label = s[i + 1 : i + 3]
                if len(label) != 2 or not label.isdigit():
                    raise ValueError(f"bad ring closure at {i}")
                i += 3
            else:
                label = ch
                i += 1
            if prev is None:
                raise ValueError(f"ring closure with no preceding atom at {i}")
            if label in ring_open:
                other, order, arom = ring_open.pop(label)
                order = order if order is not None else pending_order if pending_order is not None else 1.0
                aromatic = arom or pending_aromatic or (atoms[prev].aromatic and atoms[other].aromatic)
                bonds.append((other, prev, order, aromatic))
                atoms[other].bonds.append((prev, order, aromatic))
                atoms[prev].bonds.append((other, order, aromatic))
            else:
                ring_open[label] = (prev, pending_order, pending_aromatic)
            pending_order, pending_aromatic = None, False
            continue
        if ch == "[":
            end = s.find("]", i)
            if end < 0:
                raise ValueError("unclosed bracket atom")
            atom = _parse_bracket_atom(s[i + 1 : end])
            atoms.append(atom)
            idx = len(atoms) - 1
            atom.idx = idx
            if prev is not None:
                order = pending_order if pending_order is not None else (1.5 if atom.aromatic and atoms[prev].aromatic else 1.0)
                arom = pending_aromatic or (atom.aromatic and atoms[prev].aromatic)
                bonds.append((prev, idx, order, arom))
                atoms[prev].bonds.append((idx, order, arom))
                atom.bonds.append((prev, order, arom))
            prev = idx
            pending_order, pending_aromatic = None, False
            i = end + 1
            continue
        # organic subset atom (possibly two-letter Cl/Br)
        two = s[i : i + 2]
        if two in ("Cl", "Br"):
            element, aromatic, step = two, False, 2
        elif ch in _ORGANIC:
            element, aromatic, step = ch, False, 1
        elif ch in "bcnops" or ch == "C" or ch == "N" or ch == "O":
            element, aromatic, step = ch.upper(), True, 1
        else:
            raise ValueError(f"unexpected character {ch!r} at {i}")
        atoms.append(Atom(element=element, aromatic=aromatic))
        idx = len(atoms) - 1
        atoms[idx].idx = idx
        if prev is not None:
            order = pending_order if pending_order is not None else (1.5 if aromatic and atoms[prev].aromatic else 1.0)
            arom = pending_aromatic or (aromatic and atoms[prev].aromatic)
            bonds.append((prev, idx, order, arom))
            atoms[prev].bonds.append((idx, order, arom))
            atoms[idx].bonds.append((prev, order, arom))
        prev = idx
        pending_order, pending_aromatic = None, False
        i += step

    if ring_open:
        raise ValueError(f"unclosed ring bond(s): {sorted(ring_open)}")
    if not atoms:
        raise ValueError("no atoms parsed")
    return Molecule(atoms=atoms, n_bonds=len(bonds), smiles=s)


def _parse_bracket_atom(body: str) -> Atom:
    b = body
    isotope = ""
    while b and b[0].isdigit():
        isotope, b = isotope + b[0], b[1:]
    chirality = ""
    if b.startswith("@@"):
        chirality, b = "@@", b[2:]
    elif b.startswith("@"):
        chirality, b = "@", b[1:]
    # element
    if not b:
        raise ValueError("empty bracket atom")
    if b[0].isupper():
        element = b[0]
        b = b[1:]
        while b and b[0].islower() and not b[0] in "hn":
            element += b[0]
            b = b[1:]
    else:
        element = b[0].upper()
        b = b[1:]
    aromatic = body and body[0].islower()
    # hydrogen count
    explicit_h = 0
    if b.startswith("H"):
        b = b[1:]
        digits = ""
        while b and b[0].isdigit():
            digits, b = digits + b[0], b[1:]
        explicit_h = int(digits) if digits else 1
    # charge
    charge = 0
    if b and b[0] in "+-":
        sign = 1 if b[0] == "+" else -1
        b = b[1:]
        digits = ""
        while b and b[0].isdigit():
            digits, b = digits + b[0], b[1:]
        charge = sign * (int(digits) if digits else 1)
    return Atom(element=element, aromatic=aromatic, charge=charge, explicit_h=explicit_h,
                chirality=chirality, bracketed=True)


# --------------------------------------------------------------------------------------
# Descriptors
# --------------------------------------------------------------------------------------


def molecular_weight(mol: Molecule) -> float:
    counts = mol.formula_counts()
    return round(sum(ATOMIC_MASS.get(el, 0.0) * n for el, n in counts.items()), 2)


def hbd(mol: Molecule) -> int:
    """Hydrogen-bond donors: N/O/S atoms carrying at least one hydrogen."""
    total = 0
    for idx, atom in enumerate(mol.atoms):
        if atom.element in ("N", "O", "S"):
            if mol.implicit_h(idx) > 0:
                total += mol.implicit_h(idx)
    return total


def hba(mol: Molecule) -> int:
    """Lipinski H-bond acceptors: total N + O atoms."""
    return sum(1 for a in mol.atoms if a.element in ("N", "O"))


def ring_count(mol: Molecule) -> int:
    """Number of independent rings = E - V + C (cyclomatic number)."""
    if not mol.atoms:
        return 0
    v = len(mol.atoms)
    e = mol.n_bonds
    # connected components
    seen: set[int] = set()
    components = 0
    for start in range(v):
        if start in seen:
            continue
        components += 1
        stack = [start]
        seen.add(start)
        while stack:
            cur = stack.pop()
            for other, _, _ in mol.atoms[cur].bonds:
                if other not in seen:
                    seen.add(other)
                    stack.append(other)
    return max(0, e - v + components)


def _ring_bond_set(mol: Molecule) -> set[tuple[int, int]]:
    """Bonds that lie in at least one cycle (via DFS: non-bridge edges).

    A bond is a bridge iff removing it disconnects its component; cycles are the
    complement of the bridge set.  O(V+E) per bond component is acceptable for the
    small molecules here (MW < 1000).
    """
    ordered = [(idx, other) for idx, atom in enumerate(mol.atoms) for other, _, _ in atom.bonds]
    # unique undirected edges
    edges = sorted({tuple(sorted(pair)) for pair in ordered})
    # Tarjan bridge-finding
    adj: dict[int, list[tuple[int, int]]] = {i: [] for i in range(len(mol.atoms))}
    for eidx, (u, v) in enumerate(edges):
        adj[u].append((v, eidx))
        adj[v].append((u, eidx))
    disc = [-1] * len(mol.atoms)
    low = [0] * len(mol.atoms)
    bridges: set[int] = set()
    timer = [0]

    def dfs(u: int, parent_edge: int) -> None:
        disc[u] = low[u] = timer[0]
        timer[0] += 1
        for v, eidx in adj[u]:
            if eidx == parent_edge:
                continue
            if disc[v] == -1:
                dfs(v, eidx)
                low[u] = min(low[u], low[v])
                if low[v] > disc[u]:
                    bridges.add(eidx)
            else:
                low[u] = min(low[u], disc[v])

    for i in range(len(mol.atoms)):
        if disc[i] == -1:
            dfs(i, -1)
    return {edges[e] for e in range(len(edges)) if e not in bridges}


def rotatable_bonds(mol: Molecule) -> int:
    """Single, non-ring, non-terminal bonds between heavy atoms (amide C-N excluded)."""
    ring_bonds = _ring_bond_set(mol)
    count = 0
    seen: set[tuple[int, int]] = set()
    for idx, atom in enumerate(mol.atoms):
        for other, order, arom in atom.bonds:
            key = tuple(sorted((idx, other)))
            if key in seen:
                continue
            seen.add(key)
            if order != 1.0 or arom or key in ring_bonds:
                continue
            a, b = mol.atoms[idx], mol.atoms[other]
            if a.element == "H" or b.element == "H":
                continue
            if mol.degree(idx) < 2 or mol.degree(other) < 2:
                continue
            # exclude amide bonds C(=O)-N
            if _is_amide_bond(mol, idx, other):
                continue
            count += 1
    return count


def _is_amide_bond(mol: Molecule, i: int, j: int) -> bool:
    for a, b in ((i, j), (j, i)):
        if mol.atoms[a].element == "C" and mol.atoms[b].element == "N" and _is_carbonyl(mol, a):
            return True
    return False


def _bonded_to_carbonyl_carbon(mol: Molecule, idx: int) -> bool:
    return any(
        _is_carbonyl(mol, o) for o, _, _ in mol.atoms[idx].bonds if mol.atoms[o].element == "C"
    )


def tpsa(mol: Molecule) -> float:
    """Topological polar surface area — Ertl-style fragment approximation (Å²)."""
    total = 0.0
    for idx, atom in enumerate(mol.atoms):
        if atom.element == "O":
            if _is_carbonyl(mol, idx):
                total += _TPSA["O_carbonyl"]
            elif _has_hydrogen(mol, idx):
                total += _TPSA["O_hydroxyl"]
            else:
                total += _TPSA["O_ether"]
        elif atom.element == "N":
            if _is_aromatic_n(mol, idx):
                total += _TPSA["N_aromatic"]
            elif _is_amide_n(mol, idx):
                total += _TPSA["N_amide1"] if mol.implicit_h(idx) > 0 else _TPSA["N_amide0"]
            else:
                h = mol.implicit_h(idx)
                if h >= 2:
                    total += _TPSA["N_amine2"]
                elif h == 1:
                    total += _TPSA["N_amine1"]
                else:
                    total += _TPSA["N_amine0"]
        elif atom.element == "S" and mol.degree(idx) <= 2:
            total += _TPSA["S_thioether"]
        elif atom.element == "P":
            total += _TPSA["P"]
    return round(total, 2)


def _is_carbonyl(mol: Molecule, idx: int) -> bool:
    """True when atom ``idx`` is a carbon doubly bonded to oxygen."""
    return any(
        order == 2.0 and mol.atoms[o].element == "O"
        for o, order, _ in mol.atoms[idx].bonds
    )


def _has_hydrogen(mol: Molecule, idx: int) -> bool:
    return mol.implicit_h(idx) > 0


def _is_aromatic_n(mol: Molecule, idx: int) -> bool:
    return mol.atoms[idx].aromatic and mol.atoms[idx].element == "N"


def _is_amide_n(mol: Molecule, idx: int) -> bool:
    return any(
        mol.atoms[o].element == "C" and _is_carbonyl(mol, o)
        for o, _, _ in mol.atoms[idx].bonds
    )


def logp_fragment_estimate(mol: Molecule) -> float:
    """Heuristic fragment logP estimate.

    NOT a validated Crippen calculation.  It sums per-atom-type contributions and is
    accurate to roughly ±1.5 log units for drug-like natural products; it is used for
    triage and is labelled ``logP_estimate`` in every output.
    """
    nonpolar = 0.0
    for idx, atom in enumerate(mol.atoms):
        el = atom.element
        if el == "C":
            if atom.aromatic:
                nonpolar += _LOGP["C_aromatic"]
            elif _is_carbonyl(mol, idx):
                nonpolar += _LOGP["C_carbonyl"]
            elif any(order >= 2.0 for _, order, _ in atom.bonds):
                nonpolar += _LOGP["C_sp2"]
            else:
                nonpolar += _LOGP["C_sp3"]
        elif el == "O":
            if _is_carbonyl(mol, idx):
                nonpolar += _LOGP["O_carbonyl"]
            elif _has_hydrogen(mol, idx):
                nonpolar += _LOGP["O_hydroxyl"]
            else:
                nonpolar += _LOGP["O_ether"]
        elif el == "N":
            if _is_aromatic_n(mol, idx):
                nonpolar += _LOGP["N_aromatic"]
            elif _is_amide_n(mol, idx):
                nonpolar += _LOGP["N_amide"]
            else:
                h = mol.implicit_h(idx)
                nonpolar += {0: _LOGP["N_amine0"], 1: _LOGP["N_amine1"]}.get(h, _LOGP["N_amine2"])
        elif el == "S":
            nonpolar += _LOGP["S"]
        elif el == "P":
            nonpolar += _LOGP["P"]
        elif el in ("F", "Cl", "Br", "I"):
            nonpolar += _LOGP[el]
        if atom.charge:
            nonpolar -= 1.5 * abs(atom.charge)
    # fused-ring correction: each ring beyond the first lowers logP modestly
    nonpolar -= 0.25 * max(0, ring_count(mol) - 1)
    return round(nonpolar, 2)


def aromatic_atoms(mol: Molecule) -> int:
    return sum(1 for a in mol.atoms if a.aromatic)


def stereocentres(mol: Molecule) -> int:
    return sum(1 for a in mol.atoms if a.chirality)


def _functional_flags(mol: Molecule) -> dict[str, bool]:
    """Heuristic structural alerts relevant to assay interference and toxicity."""
    flags: dict[str, bool] = {
        "michael_acceptor": False,
        "catechol": False,
        "quinone": False,
        "nitro": False,
        "polyunsaturated": False,
        "high_logp": False,
    }
    # Michael acceptor: C=C where either alkene carbon is (or is adjacent to) a C=O
    seen_pairs: set[tuple[int, int]] = set()
    for idx, atom in enumerate(mol.atoms):
        if atom.element != "C":
            continue
        for other, order, _ in atom.bonds:
            if order != 2.0 or mol.atoms[other].element != "C":
                continue
            key = tuple(sorted((idx, other)))
            if key in seen_pairs:
                continue
            seen_pairs.add(key)
            if (
                _is_carbonyl(mol, idx)
                or _is_carbonyl(mol, other)
                or _bonded_to_carbonyl_carbon(mol, idx)
                or _bonded_to_carbonyl_carbon(mol, other)
            ):
                flags["michael_acceptor"] = True
    # catechol: aromatic C with two adjacent OH-bearing aromatic carbons
    for idx, atom in enumerate(mol.atoms):
        if atom.element == "C" and atom.aromatic:
            hydroxyls = [o for o, _, _ in atom.bonds if mol.atoms[o].element == "O" and mol.implicit_h(o) > 0]
            for o in hydroxyls:
                for o2, _, _ in atom.bonds:
                    if o2 == o:
                        continue
                    if mol.atoms[o2].element == "C" and mol.atoms[o2].aromatic:
                        if any(mol.atoms[n].element == "O" and mol.implicit_h(n) > 0 for n, _, _ in mol.atoms[o2].bonds):
                            flags["catechol"] = True
    # quinone: two carbonyl carbons close in the same ring system
    for ring in _six_carbon_rings(mol):
        carbonyls = [i for i in ring if _is_carbonyl(mol, i)]
        if len(carbonyls) == 2:
            flags["quinone"] = True
    # nitro: N bonded to two O (>=1 double)
    for idx, atom in enumerate(mol.atoms):
        if atom.element == "N":
            oxygens = sum(1 for o, _, _ in atom.bonds if mol.atoms[o].element == "O")
            if oxygens >= 2:
                flags["nitro"] = True
    double_bonds = sum(1 for a in mol.atoms for _, order, _ in a.bonds if order == 2.0) // 2
    flags["polyunsaturated"] = double_bonds >= 5
    return flags


def _six_carbon_rings(mol: Molecule) -> list[list[int]]:
    """Enumerate unique six-membered all-carbon rings (SMALL molecules only)."""
    rings: list[list[int]] = []
    seen: set[frozenset[int]] = set()
    carbon = {i for i, a in enumerate(mol.atoms) if a.element == "C"}

    def dfs(start: int, current: int, path: list[int]) -> None:
        if len(path) == 6:
            if start in {o for o, _, _ in mol.atoms[current].bonds}:
                key = frozenset(path)
                if key not in seen:
                    seen.add(key)
                    rings.append(list(path))
            return
        for other, _, _ in mol.atoms[current].bonds:
            if other not in carbon or other in path:
                continue
            # keep only the lexicographically smallest rotation to avoid duplicates
            if other < start:
                continue
            dfs(start, other, path + [other])

    for start in sorted(carbon):
        dfs(start, start, [start])
    return rings


def _graph_distance(mol: Molecule, a: int, b: int) -> int:
    if a == b:
        return 0
    seen = {a}
    frontier = [a]
    dist = 0
    while frontier:
        dist += 1
        nxt: list[int] = []
        for cur in frontier:
            for other, _, _ in mol.atoms[cur].bonds:
                if other == b:
                    return dist
                if other not in seen:
                    seen.add(other)
                    nxt.append(other)
        frontier = nxt
    return 10**6


def synthetic_accessibility_heuristic(mol: Molecule) -> float:
    """Crude 1–10 accessibility score (1 = easy, 10 = hard).

    Based on stereocentre count, ring complexity and molecular size.  It is a
    *heuristic*, not a retrosynthesis feasibility judgement; flagged in output.
    """
    score = 1.0
    score += 0.6 * stereocentres(mol)
    score += 0.4 * max(0, ring_count(mol) - 2)
    score += 0.15 * max(0, molecular_weight(mol) - 400) / 100.0
    return round(min(10.0, score), 2)


@dataclass
class Descriptors:
    """Computed molecular descriptors for one candidate."""

    smiles: str
    valid: bool
    formula: str
    mw: float
    logp_estimate: float
    hbd: int
    hba: int
    tpsa: float
    rings: int
    rotatable_bonds: int
    aromatic_atoms: int
    stereocentres: int
    lipinski_pass: bool
    lipinski_violations: int
    veber_pass: bool
    sa_score_heuristic: float
    flags: dict[str, bool]
    note: str = "logP and TPSA are transparent fragment approximations; SA score is a heuristic."

    def to_dict(self) -> dict:
        return {
            "smiles": self.smiles,
            "valid": self.valid,
            "formula": self.formula,
            "mw": self.mw,
            "logp_estimate": self.logp_estimate,
            "hbd": self.hbd,
            "hba": self.hba,
            "tpsa": self.tpsa,
            "rings": self.rings,
            "rotatable_bonds": self.rotatable_bonds,
            "aromatic_atoms": self.aromatic_atoms,
            "stereocentres": self.stereocentres,
            "lipinski_pass": self.lipinski_pass,
            "lipinski_violations": self.lipinski_violations,
            "veber_pass": self.veber_pass,
            "sa_score_heuristic": self.sa_score_heuristic,
            "flags": self.flags,
            "note": self.note,
        }


def _formula(mol: Molecule) -> str:
    counts = mol.formula_counts()
    order = ["C", "H"] + sorted(el for el in counts if el not in ("C", "H"))
    return "".join(f"{el}{counts[el] if counts[el] > 1 else ''}" for el in order if counts.get(el))


def describe_smiles(smiles: str) -> Descriptors:
    """Parse SMILES and compute the descriptor block; invalid input is explicit."""
    try:
        mol = parse_smiles(smiles)
    except ValueError as exc:
        return Descriptors(
            smiles=smiles, valid=False, formula="", mw=0.0, logp_estimate=0.0, hbd=0, hba=0,
            tpsa=0.0, rings=0, rotatable_bonds=0, aromatic_atoms=0, stereocentres=0,
            lipinski_pass=False, lipinski_violations=99, veber_pass=False,
            sa_score_heuristic=10.0, flags={"parse_error": True},
            note=f"SMILES could not be parsed: {exc}",
        )
    mw = molecular_weight(mol)
    logp = logp_fragment_estimate(mol)
    violations = 0
    violations += mw > 500
    violations += logp > 5
    violations += hbd(mol) > 5
    violations += hba(mol) > 10
    rb = rotatable_bonds(mol)
    t = tpsa(mol)
    return Descriptors(
        smiles=smiles,
        valid=True,
        formula=_formula(mol),
        mw=mw,
        logp_estimate=logp,
        hbd=hbd(mol),
        hba=hba(mol),
        tpsa=t,
        rings=ring_count(mol),
        rotatable_bonds=rb,
        aromatic_atoms=aromatic_atoms(mol),
        stereocentres=stereocentres(mol),
        lipinski_pass=violations <= 1,
        lipinski_violations=violations,
        veber_pass=rb <= 10 and t <= 140,
        sa_score_heuristic=synthetic_accessibility_heuristic(mol),
        flags=_functional_flags(mol),
    )
