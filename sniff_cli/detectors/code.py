import ast
import re

class CodeDetector:
    def __init__(self):
        pass

    def analyze(self, diff: str) -> dict:
        if not diff or not str(diff).strip():
            return {"score": 0.0, "reason": "No code added"}

        lines = diff.split('\n')
        total_lines = len(lines)
        if total_lines == 0:
            return {"score": 0.0, "reason": "No valid diff lines"}

        # Try to parse as python AST
        try:
            tree = ast.parse(diff)
            # AST parsed successfully, we can do structural analysis
            return self._analyze_ast(tree, total_lines)
        except SyntaxError:
            # Not valid python or a partial snippet. Fall back to heuristical entropy
            return self._analyze_raw(diff, total_lines)

    def _analyze_ast(self, tree, total_lines):
        score = 0.0
        reasons = []

        num_nodes = 0
        docstrings = 0
        vars_assigned = set()

        for node in ast.walk(tree):
            num_nodes += 1
            if isinstance(node, (ast.FunctionDef, ast.ClassDef, ast.Module)):
                if ast.get_docstring(node):
                    docstrings += 1
            if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store):
                vars_assigned.add(node.id)
        
        node_density = num_nodes / total_lines if total_lines > 0 else 0

        if total_lines > 15 and docstrings > 0:
            score += 0.4
            reasons.append(f"High structural docstring density ({docstrings} docstrings / {total_lines} LOC)")

        if total_lines > 20 and len(vars_assigned) < (total_lines / 5):
            score += 0.3
            reasons.append(f"Low AST lexical entropy (repetitive variable space: {len(vars_assigned)} unique vars)")

        if total_lines > 50:
            score += 0.2
            reasons.append("Large structural block addition")

        return {"score": min(score, 1.0), "reason": "; ".join(reasons) if reasons else "Organic AST structural complexity"}

    def _analyze_raw(self, diff: str, total_lines: int):
        score = 0.0
        reasons = []
        comment_lines = sum(1 for line in diff.split('\n') if line.strip().startswith('#') or line.strip().startswith('//'))
        if total_lines > 40:
             score += 0.4
             reasons.append("Large raw code block addition")
        if total_lines > 10 and (comment_lines / total_lines) > 0.15:
             score += 0.5
             reasons.append("Unusually high raw comment density")
             
        # Catch common LLM scaffolding patterns
        if "console.log" in diff and "TODO" not in diff and total_lines > 5:
             score += 0.2
        if "useState" in diff and "useEffect" in diff:
             score += 0.3
             reasons.append("Generic React component scaffolding detected")

        return {"score": min(score, 1.0), "reason": "; ".join(reasons) if reasons else "Organic raw complexity"}
