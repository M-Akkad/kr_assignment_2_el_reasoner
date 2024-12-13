#!/usr/bin/env python3

import sys
from py4j.java_gateway import JavaGateway
from typing import Dict, Set, List


class ELReasoner:
    def __init__(self):
        # Initialize Java gateway and components
        self.gateway = JavaGateway()
        self.parser = self.gateway.getOWLParser()
        self.formatter = self.gateway.getSimpleDLFormatter()
        self.el_factory = self.gateway.getELFactory()

        # Data structures for completion algorithm
        self.concepts: Dict[str, Set[str]] = {}  # Maps elements to assigned concepts
        self.successors: Dict[str, Dict[str, str]] = (
            {}
        )  # Maps elements to role successors
        self.initial_concepts: Dict[str, str] = {}  # Maps elements to initial concepts
        self.ontology = None

    def load_ontology(self, file_path: str) -> None:
        """Load and prepare the ontology"""
        self.ontology = self.parser.parseFile(file_path)
        self.gateway.convertToBinaryConjunctions(self.ontology)

    def initialize_element(self, element: str, concept: str) -> None:
        """Initialize a new element with a concept"""
        if element not in self.concepts:
            self.concepts[element] = set([concept])
            self.initial_concepts[element] = concept
            self.successors[element] = {}

    def apply_top_rule(self, element: str) -> bool:
        """⊤-rule: Add ⊤ to any individual"""
        if "T" not in self.concepts[element]:
            self.concepts[element].add("T")
            return True
        return False

    def apply_conjunction_rules(self, element: str) -> bool:
        """Apply both conjunction rules"""
        changed = False
        concepts = self.concepts[element]

        for concept in self.ontology.getSubConcepts():
            if concept.getClass().getSimpleName() == "ConceptConjunction":
                conjuncts = [self.formatter.format(c) for c in concept.getConjuncts()]
                conj_name = self.formatter.format(concept)

                # ⊓-rule 1
                if conj_name in concepts:
                    for conjunct in conjuncts:
                        if conjunct not in concepts:
                            concepts.add(conjunct)
                            changed = True

                # ⊓-rule 2
                if all(c in concepts for c in conjuncts):
                    if conj_name not in concepts:
                        concepts.add(conj_name)
                        changed = True

        return changed

    def apply_existential_rules(self, element: str) -> bool:
        """Apply both existential rules"""
        changed = False

        # ∃-rule 1
        for concept in self.ontology.getSubConcepts():
            if concept.getClass().getSimpleName() == "ExistentialRoleRestriction":
                concept_str = self.formatter.format(concept)
                if concept_str in self.concepts[element]:
                    role = self.formatter.format(concept.role())
                    filler = self.formatter.format(concept.filler())

                    # Check for existing successor with initial concept
                    successor_found = False
                    for succ, succ_role in self.successors[element].items():
                        if succ_role == role and self.initial_concepts[succ] == filler:
                            successor_found = True
                            break

                    if not successor_found:
                        # Create new successor
                        new_succ = f"{element}_succ_{len(self.successors[element])}"
                        self.initialize_element(new_succ, filler)
                        self.successors[element][new_succ] = role
                        changed = True

        # ∃-rule 2
        for succ, role in self.successors[element].items():
            for concept in self.concepts[succ]:
                existential = f"∃{role}.{concept}"
                if existential not in self.concepts[element]:
                    self.concepts[element].add(existential)
                    changed = True

        return changed

    def apply_subsumption_rule(self, element: str) -> bool:
        changed = False
        concepts = self.concepts[element]

        for axiom in self.ontology.tbox().getAxioms():
            if axiom.getClass().getSimpleName() == "EquivalenceAxiom":
                concepts_in_equiv = [self.formatter.format(c) for c in axiom.getConcepts()]

                # If any concept in the equivalence is in our set,
                # add all other concepts in the equivalence
                if any(c in concepts for c in concepts_in_equiv):
                    for concept in concepts_in_equiv:
                        if concept not in concepts:
                            concepts.add(concept)
                            changed = True

            elif axiom.getClass().getSimpleName() == "GeneralConceptInclusion":
                lhs = self.formatter.format(axiom.lhs())
                rhs = self.formatter.format(axiom.rhs())

                if lhs in concepts and rhs not in concepts:
                    concepts.add(rhs)
                    changed = True

        return changed

    def compute_subsumers(self, class_name: str) -> Set[str]:
        """Main method to compute all subsumers of a given class name"""
        # Add quotes if not present
        if not class_name.startswith('"'):
            class_name = f'"{class_name}"'

        # Initialize with class_name
        initial_element = "d0"
        self.initialize_element(initial_element, class_name)

        # Compute all subsumers
        changed = True
        while changed:
            changed = False
            for element in list(self.concepts.keys()):
                changed |= self.apply_top_rule(element)
                changed |= self.apply_conjunction_rules(element)
                changed |= self.apply_existential_rules(element)
                changed |= self.apply_subsumption_rule(element)

        # Collect all named concepts and T
        subsumers = set()
        for concept in self.concepts[initial_element]:
            if (concept.startswith('"') and concept.endswith('"')) or concept == "T":  # Changed from "TOP" to "T"
                subsumers.add(concept.strip('"'))  # Remove quotes for cleaner output

        return subsumers


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

        # Output results in sorted order
        for subsumer in sorted(subsumers):
            print(subsumer)

    except Exception as e:
        print(f"Error: {str(e)}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
