#!/usr/bin/env python3

import sys
from py4j.java_gateway import JavaGateway
from typing import Dict, Set, List, Tuple

class ELReasoner:
    def __init__(self):
        # Initialize Java gateway and components
        self.gateway = JavaGateway()
        self.parser = self.gateway.getOWLParser()
        self.formatter = self.gateway.getSimpleDLFormatter()
        self.el_factory = self.gateway.getELFactory()

        # Data structures for completion algorithm
        self.concepts: Dict[str, Set[str]] = {}  # Maps elements to assigned concepts
        self.successors: Dict[str, Dict[str, str]] = {}  # Maps elements to role successors
        self.initial_concepts: Dict[str, str] = {}  # Maps elements to initial concepts
        self.gci_axioms: List[Tuple[str, str]] = []  # Store GCIs including those from equivalence axioms
        self.ontology = None

    def load_ontology(self, file_path: str) -> None:
        """Load and prepare the ontology"""
        self.ontology = self.parser.parseFile(file_path)
        self.gateway.convertToBinaryConjunctions(self.ontology)

        # Store GCIs and processed equivalence axioms
        self.gci_axioms = []

        # Process all axioms
        for axiom in self.ontology.tbox().getAxioms():
            axiom_type = axiom.getClass().getSimpleName()

            if axiom_type == "EquivalenceAxiom":
                # Convert A ≡ B into A ⊑ B and B ⊑ A
                concepts = list(axiom.getConcepts())
                for i in range(len(concepts)):
                    for j in range(len(concepts)):
                        if i != j:
                            lhs = self.formatter.format(concepts[i])
                            rhs = self.formatter.format(concepts[j])
                            self.gci_axioms.append((lhs, rhs))
                            # Add reverse direction
                            self.gci_axioms.append((rhs, lhs))

            elif axiom_type == "GeneralConceptInclusion":
                lhs = self.formatter.format(axiom.lhs())
                rhs = self.formatter.format(axiom.rhs())
                self.gci_axioms.append((lhs, rhs))

    def initialize_element(self, element: str, concept: str) -> None:
        """Initialize a new element with a concept"""
        if element not in self.concepts:
            self.concepts[element] = set([concept])
            self.initial_concepts[element] = concept
            self.successors[element] = {}

    def apply_top_rule(self, element: str) -> bool:
        """⊤-rule: Add ⊤ to any individual"""
        if "TOP" not in self.concepts[element]:
            self.concepts[element].add("TOP")
            return True
        return False

    def apply_conjunction_rules(self, element: str) -> bool:
        """Apply both conjunction rules"""
        changed = False
        concepts = self.concepts[element]

        # ⊓-rule 1: If d has C ⊓ D assigned, assign also C and D to d
        for concept in list(concepts):
            if isinstance(concept, str) and "⊓" in concept:
                parts = concept.split(" ⊓ ")
                for part in parts:
                    if part not in concepts:
                        concepts.add(part)
                        changed = True

        # ⊓-rule 2: If d has C and D assigned, assign also C ⊓ D to d
        # Only create conjunctions that appear in the input
        input_concepts = set()
        for lhs, rhs in self.gci_axioms:
            input_concepts.add(lhs)
            input_concepts.add(rhs)

        concept_list = sorted(list(concepts & input_concepts))
        for i in range(len(concept_list)):
            for j in range(i + 1, len(concept_list)):
                conj = f"{concept_list[i]} ⊓ {concept_list[j]}"
                if conj in input_concepts and conj not in concepts:
                    concepts.add(conj)
                    changed = True

        return changed

    def apply_existential_rules(self, element: str) -> bool:
        """Apply both existential rules"""
        changed = False

        # ∃-rule 1: If d has ∃r.C assigned
        for concept in list(self.concepts[element]):
            if isinstance(concept, str) and concept.startswith("∃"):
                role = concept[1:concept.find(".")]
                filler = concept[concept.find(".")+1:]

                # Check if there's already a suitable successor
                has_successor = False
                for succ, succ_role in self.successors[element].items():
                    if succ_role == role and self.initial_concepts.get(succ) == filler:
                        has_successor = True
                        break

                if not has_successor:
                    # Try to reuse existing element with matching initial concept
                    reused = False
                    for e, init_concept in self.initial_concepts.items():
                        if init_concept == filler:
                            self.successors[element][e] = role
                            reused = True
                            changed = True
                            break

                    # If no existing element could be reused, create new one
                    if not reused:
                        new_succ = f"{element}_succ_{len(self.successors[element])}"
                        self.initialize_element(new_succ, filler)
                        self.successors[element][new_succ] = role
                        changed = True

        # ∃-rule 2: If d has an r-successor with C assigned
        for succ, role in list(self.successors[element].items()):
            for concept in list(self.concepts[succ]):
                existential = f"∃{role}.{concept}"
                if existential not in self.concepts[element]:
                    self.concepts[element].add(existential)
                    changed = True

        return changed

    def apply_subsumption_rule(self, element: str) -> bool:
        """⊑-rule: If d has C assigned and C ⊑ D ∈ T, then also assign D to d"""
        changed = False
        concepts = set(self.concepts[element])  # Create a copy to avoid modification during iteration

        # Process all GCIs (including those from equivalence axioms)
        for lhs, rhs in self.gci_axioms:
            if lhs in self.concepts[element] and rhs not in self.concepts[element]:
                self.concepts[element].add(rhs)
                changed = True

                # Check for equivalence by looking for reverse GCI
                reverse_pair = (rhs, lhs)
                if reverse_pair in self.gci_axioms:
                    # If this is part of an equivalence axiom, also add any concepts
                    # that follow from the equivalence
                    for other_gci in self.gci_axioms:
                        if other_gci[0] == rhs and other_gci[1] not in self.concepts[element]:
                            self.concepts[element].add(other_gci[1])
                            changed = True

        return changed

    def compute_subsumers(self, class_name: str) -> Set[str]:
        """Main method to compute all subsumers of a given class name"""
        # Add quotes if not present
        if not class_name.startswith('"'):
            class_name = f'"{class_name}"'
        if not class_name.endswith('"'):
            class_name = f'{class_name}"'

        # Initialize with class_name
        initial_element = "d0"
        self.initialize_element(initial_element, class_name)

        # Apply rules until fixpoint
        changed = True
        max_iterations = len(self.gci_axioms) * 10  # Reasonable upper bound
        iteration_count = 0

        while changed and iteration_count < max_iterations:
            changed = False
            iteration_count += 1

            # Apply all rules to all existing elements
            for element in list(self.concepts.keys()):
                changed |= self.apply_top_rule(element)
                changed |= self.apply_conjunction_rules(element)
                changed |= self.apply_existential_rules(element)
                changed |= self.apply_subsumption_rule(element)

        # Return only named concepts and TOP
        return {c for c in self.concepts["d0"] 
                if (c.startswith('"') and c.endswith('"')) or c == "TOP"}

def main():
    try:
        if len(sys.argv) != 3:
            print("Usage: python el_reasoner.py ONTOLOGY_FILE CLASS_NAME", file=sys.stderr)
            sys.exit(1)

        ontology_file = sys.argv[1]
        class_name = sys.argv[2]

        reasoner = ELReasoner()
        reasoner.load_ontology(ontology_file)
        subsumers = reasoner.compute_subsumers(class_name)

        # Output results one per line
        for subsumer in sorted(subsumers):
            print(subsumer)

    except Exception as e:
        print(f"Error: {str(e)}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()