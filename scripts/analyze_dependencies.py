#!/usr/bin/env python3
"""
Dependency Analysis Script for Streamware

Analyzes:
1. Import dependencies between modules
2. Duplicated code patterns
3. Legacy/unused code
4. Circular dependencies

Usage:
    python scripts/analyze_dependencies.py [--output report.md]
"""

import ast
import os
import sys
import hashlib
import argparse
from pathlib import Path
from collections import defaultdict
from typing import Dict, List, Set, Tuple, Optional
from dataclasses import dataclass, field


@dataclass
class ModuleInfo:
    """Information about a Python module."""
    path: Path
    name: str
    imports: List[str] = field(default_factory=list)
    from_imports: Dict[str, List[str]] = field(default_factory=dict)
    classes: List[str] = field(default_factory=list)
    functions: List[str] = field(default_factory=list)
    lines: int = 0
    size_bytes: int = 0


@dataclass
class CodeBlock:
    """A block of code for duplicate detection."""
    file: str
    start_line: int
    end_line: int
    content: str
    hash: str


def get_project_root() -> Path:
    """Get the project root directory."""
    script_dir = Path(__file__).parent
    return script_dir.parent


def find_python_files(root: Path) -> List[Path]:
    """Find all Python files in the project."""
    python_files = []
    exclude_dirs = {'venv', '.venv', '__pycache__', '.git', 'node_modules', '.eggs', 'build', 'dist'}
    
    for path in root.rglob('*.py'):
        if not any(exc in path.parts for exc in exclude_dirs):
            python_files.append(path)
    
    return sorted(python_files)


def parse_module(file_path: Path, project_root: Path) -> Optional[ModuleInfo]:
    """Parse a Python module and extract information."""
    try:
        content = file_path.read_text(encoding='utf-8')
        tree = ast.parse(content)
    except (SyntaxError, UnicodeDecodeError) as e:
        print(f"  ⚠️ Could not parse {file_path}: {e}")
        return None
    
    rel_path = file_path.relative_to(project_root)
    module_name = str(rel_path).replace('/', '.').replace('\\', '.').replace('.py', '')
    
    info = ModuleInfo(
        path=file_path,
        name=module_name,
        lines=len(content.splitlines()),
        size_bytes=len(content.encode('utf-8'))
    )
    
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                info.imports.append(alias.name)
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ''
            names = [alias.name for alias in node.names]
            if module in info.from_imports:
                info.from_imports[module].extend(names)
            else:
                info.from_imports[module] = names
        elif isinstance(node, ast.ClassDef):
            info.classes.append(node.name)
        elif isinstance(node, ast.FunctionDef) or isinstance(node, ast.AsyncFunctionDef):
            # Only top-level functions
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                info.functions.append(node.name)
    
    return info


def analyze_dependencies(modules: List[ModuleInfo]) -> Dict[str, Set[str]]:
    """Build dependency graph between modules."""
    deps = defaultdict(set)
    module_names = {m.name for m in modules}
    
    for module in modules:
        # Check direct imports
        for imp in module.imports:
            # Check if it's an internal import
            for name in module_names:
                if imp == name or imp.startswith(name + '.') or name.startswith(imp + '.'):
                    deps[module.name].add(name)
        
        # Check from imports
        for from_module, names in module.from_imports.items():
            # Handle relative imports
            if from_module.startswith('.'):
                # Convert relative to absolute
                parts = module.name.split('.')
                level = len(from_module) - len(from_module.lstrip('.'))
                if level <= len(parts):
                    base = '.'.join(parts[:-level]) if level > 0 else module.name
                    abs_module = base + '.' + from_module.lstrip('.') if from_module.lstrip('.') else base
                    for name in module_names:
                        if abs_module == name or name.startswith(abs_module + '.'):
                            deps[module.name].add(name)
            else:
                for name in module_names:
                    if from_module == name or from_module.startswith(name + '.') or name.startswith(from_module + '.'):
                        deps[module.name].add(name)
    
    return deps


def find_circular_dependencies(deps: Dict[str, Set[str]]) -> List[List[str]]:
    """Find circular dependencies in the dependency graph."""
    cycles = []
    visited = set()
    rec_stack = []
    
    def dfs(node: str, path: List[str]):
        if node in path:
            cycle_start = path.index(node)
            cycle = path[cycle_start:] + [node]
            if cycle not in cycles:
                cycles.append(cycle)
            return
        
        if node in visited:
            return
        
        visited.add(node)
        path.append(node)
        
        for neighbor in deps.get(node, []):
            dfs(neighbor, path.copy())
    
    for node in deps:
        dfs(node, [])
    
    return cycles


def find_duplicate_code(files: List[Path], min_lines: int = 6) -> List[Tuple[CodeBlock, CodeBlock]]:
    """Find duplicate code blocks across files."""
    blocks = []
    
    for file_path in files:
        try:
            content = file_path.read_text(encoding='utf-8')
            lines = content.splitlines()
        except:
            continue
        
        # Extract function and class bodies
        try:
            tree = ast.parse(content)
        except:
            continue
        
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                if hasattr(node, 'lineno') and hasattr(node, 'end_lineno'):
                    start = node.lineno - 1
                    end = node.end_lineno
                    if end - start >= min_lines:
                        block_content = '\n'.join(lines[start:end])
                        # Normalize whitespace for comparison
                        normalized = '\n'.join(line.strip() for line in lines[start:end] if line.strip())
                        block_hash = hashlib.md5(normalized.encode()).hexdigest()
                        
                        blocks.append(CodeBlock(
                            file=str(file_path),
                            start_line=start + 1,
                            end_line=end,
                            content=block_content,
                            hash=block_hash
                        ))
    
    # Find duplicates by hash
    hash_to_blocks = defaultdict(list)
    for block in blocks:
        hash_to_blocks[block.hash].append(block)
    
    duplicates = []
    for hash_val, block_list in hash_to_blocks.items():
        if len(block_list) > 1:
            for i in range(len(block_list)):
                for j in range(i + 1, len(block_list)):
                    duplicates.append((block_list[i], block_list[j]))
    
    return duplicates


def find_similar_functions(modules: List[ModuleInfo]) -> List[Tuple[str, str, List[str]]]:
    """Find functions with similar names that might be duplicates."""
    all_functions = []
    
    for module in modules:
        for func in module.functions:
            all_functions.append((module.name, func))
    
    # Group by base name (without prefixes/suffixes)
    similar = defaultdict(list)
    for module, func in all_functions:
        # Normalize function name
        base = func.lower().replace('_', '')
        similar[base].append((module, func))
    
    results = []
    for base, funcs in similar.items():
        if len(funcs) > 1:
            modules_funcs = [(m, f) for m, f in funcs]
            results.append((base, [f"{m}.{f}" for m, f in modules_funcs]))
    
    return [(base, funcs) for base, funcs in results if len(funcs) > 1]


def find_unused_imports(file_path: Path) -> List[str]:
    """Find imports that are not used in a file."""
    try:
        content = file_path.read_text(encoding='utf-8')
        tree = ast.parse(content)
    except:
        return []
    
    imported_names = set()
    used_names = set()
    
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                name = alias.asname or alias.name.split('.')[0]
                imported_names.add(name)
        elif isinstance(node, ast.ImportFrom):
            for alias in node.names:
                name = alias.asname or alias.name
                if name != '*':
                    imported_names.add(name)
        elif isinstance(node, ast.Name):
            used_names.add(node.id)
        elif isinstance(node, ast.Attribute):
            # Get the root name
            n = node
            while isinstance(n, ast.Attribute):
                n = n.value
            if isinstance(n, ast.Name):
                used_names.add(n.id)
    
    unused = imported_names - used_names
    return list(unused)


def find_legacy_patterns(files: List[Path]) -> Dict[str, List[Tuple[str, int]]]:
    """Find legacy code patterns."""
    patterns = {
        'print_debug': r'print\s*\(',  # print statements (should use logging)
        'bare_except': r'except\s*:',  # bare except clauses
        'old_string_format': r'%\s*\(',  # old-style string formatting
        'type_comments': r'#\s*type:',  # type comments (use annotations)
        'todo_fixme': r'#\s*(TODO|FIXME|XXX|HACK)',  # unresolved TODOs
    }
    
    import re
    results = defaultdict(list)
    
    for file_path in files:
        try:
            content = file_path.read_text(encoding='utf-8')
            lines = content.splitlines()
        except:
            continue
        
        for i, line in enumerate(lines, 1):
            for pattern_name, pattern in patterns.items():
                if re.search(pattern, line):
                    results[pattern_name].append((str(file_path), i))
    
    return results


def generate_report(
    project_root: Path,
    modules: List[ModuleInfo],
    deps: Dict[str, Set[str]],
    cycles: List[List[str]],
    duplicates: List[Tuple[CodeBlock, CodeBlock]],
    similar_funcs: List[Tuple[str, List[str]]],
    legacy_patterns: Dict[str, List[Tuple[str, int]]],
    unused_imports: Dict[str, List[str]],
) -> str:
    """Generate a markdown report."""
    lines = []
    lines.append("# Streamware Dependency Analysis Report\n")
    lines.append(f"Project root: `{project_root}`\n")
    lines.append(f"Total modules: {len(modules)}\n")
    lines.append(f"Total lines of code: {sum(m.lines for m in modules):,}\n")
    
    # Module summary
    lines.append("\n## 📦 Module Summary\n")
    lines.append("| Module | Lines | Classes | Functions |")
    lines.append("|--------|-------|---------|-----------|")
    for m in sorted(modules, key=lambda x: x.lines, reverse=True)[:20]:
        lines.append(f"| `{m.name}` | {m.lines} | {len(m.classes)} | {len(m.functions)} |")
    
    # Dependency graph
    lines.append("\n## 🔗 Dependency Structure\n")
    lines.append("```mermaid")
    lines.append("graph TD")
    
    # Group by package
    packages = defaultdict(list)
    for m in modules:
        parts = m.name.split('.')
        pkg = parts[0] if len(parts) > 1 else 'root'
        packages[pkg].append(m.name)
    
    # Add subgraphs for packages
    for pkg, pkg_modules in packages.items():
        if pkg != 'root' and len(pkg_modules) > 1:
            lines.append(f"    subgraph {pkg}")
            for mod in pkg_modules[:10]:  # Limit to avoid huge graphs
                short_name = mod.split('.')[-1]
                lines.append(f"        {mod.replace('.', '_')}[{short_name}]")
            lines.append("    end")
    
    # Add edges (limited)
    edge_count = 0
    for src, targets in deps.items():
        for tgt in targets:
            if src != tgt and edge_count < 50:
                lines.append(f"    {src.replace('.', '_')} --> {tgt.replace('.', '_')}")
                edge_count += 1
    
    lines.append("```\n")
    
    # Circular dependencies
    lines.append("\n## 🔄 Circular Dependencies\n")
    if cycles:
        lines.append(f"Found **{len(cycles)}** circular dependency chains:\n")
        for cycle in cycles[:10]:
            lines.append(f"- `{' → '.join(cycle)}`")
    else:
        lines.append("✅ No circular dependencies found.\n")
    
    # Duplicate code
    lines.append("\n## 📋 Duplicate Code\n")
    if duplicates:
        lines.append(f"Found **{len(duplicates)}** duplicate code blocks:\n")
        for b1, b2 in duplicates[:10]:
            lines.append(f"### Duplicate pair")
            lines.append(f"- `{b1.file}:{b1.start_line}-{b1.end_line}`")
            lines.append(f"- `{b2.file}:{b2.start_line}-{b2.end_line}`")
            lines.append("")
    else:
        lines.append("✅ No exact duplicate code blocks found.\n")
    
    # Similar functions
    lines.append("\n## 🔍 Similar Function Names\n")
    lines.append("Functions with similar names that might be candidates for consolidation:\n")
    if similar_funcs:
        for base, funcs in similar_funcs[:15]:
            lines.append(f"- **{base}**: {', '.join(f'`{f}`' for f in funcs[:5])}")
    else:
        lines.append("✅ No similar function names found.\n")
    
    # Legacy patterns
    lines.append("\n## ⚠️ Legacy Code Patterns\n")
    for pattern_name, occurrences in legacy_patterns.items():
        if occurrences:
            lines.append(f"\n### {pattern_name.replace('_', ' ').title()} ({len(occurrences)} occurrences)")
            for file_path, line_num in occurrences[:5]:
                rel_path = Path(file_path).relative_to(project_root)
                lines.append(f"- `{rel_path}:{line_num}`")
            if len(occurrences) > 5:
                lines.append(f"- ... and {len(occurrences) - 5} more")
    
    # Unused imports
    lines.append("\n## 🗑️ Potentially Unused Imports\n")
    files_with_unused = [(f, imps) for f, imps in unused_imports.items() if imps]
    if files_with_unused:
        lines.append(f"Found unused imports in **{len(files_with_unused)}** files:\n")
        for file_path, imports in sorted(files_with_unused, key=lambda x: len(x[1]), reverse=True)[:10]:
            rel_path = Path(file_path).relative_to(project_root)
            lines.append(f"- `{rel_path}`: {', '.join(f'`{i}`' for i in imports[:5])}")
            if len(imports) > 5:
                lines.append(f"  - ... and {len(imports) - 5} more")
    else:
        lines.append("✅ No unused imports detected.\n")
    
    # Recommendations
    lines.append("\n## 💡 Recommendations\n")
    recommendations = []
    
    if cycles:
        recommendations.append("1. **Fix circular dependencies** - Consider restructuring imports or using lazy imports")
    if duplicates:
        recommendations.append("2. **Consolidate duplicate code** - Extract common functionality into shared utilities")
    if legacy_patterns.get('print_debug'):
        recommendations.append("3. **Replace print statements** - Use `logging` module for better control")
    if legacy_patterns.get('bare_except'):
        recommendations.append("4. **Avoid bare except** - Catch specific exceptions")
    if legacy_patterns.get('todo_fixme'):
        recommendations.append("5. **Address TODOs** - Review and resolve pending tasks")
    
    if recommendations:
        lines.extend(recommendations)
    else:
        lines.append("✅ Code looks clean! No major issues found.")
    
    return '\n'.join(lines)


def main():
    parser = argparse.ArgumentParser(description='Analyze project dependencies')
    parser.add_argument('--output', '-o', default='dependency_report.md', help='Output file')
    args = parser.parse_args()
    
    project_root = get_project_root()
    print(f"📁 Analyzing project: {project_root}")
    
    # Find all Python files
    print("🔍 Finding Python files...")
    python_files = find_python_files(project_root)
    print(f"   Found {len(python_files)} Python files")
    
    # Parse modules
    print("📖 Parsing modules...")
    modules = []
    for f in python_files:
        info = parse_module(f, project_root)
        if info:
            modules.append(info)
    print(f"   Parsed {len(modules)} modules")
    
    # Analyze dependencies
    print("🔗 Analyzing dependencies...")
    deps = analyze_dependencies(modules)
    
    # Find circular dependencies
    print("🔄 Checking for circular dependencies...")
    cycles = find_circular_dependencies(deps)
    print(f"   Found {len(cycles)} circular dependency chains")
    
    # Find duplicate code
    print("📋 Scanning for duplicate code...")
    duplicates = find_duplicate_code(python_files)
    print(f"   Found {len(duplicates)} duplicate code blocks")
    
    # Find similar functions
    print("🔍 Finding similar function names...")
    similar_funcs = find_similar_functions(modules)
    
    # Find legacy patterns
    print("⚠️ Scanning for legacy patterns...")
    legacy_patterns = find_legacy_patterns(python_files)
    
    # Find unused imports
    print("🗑️ Checking for unused imports...")
    unused_imports = {}
    for f in python_files:
        unused = find_unused_imports(f)
        if unused:
            unused_imports[str(f)] = unused
    
    # Generate report
    print("📝 Generating report...")
    report = generate_report(
        project_root, modules, deps, cycles, duplicates,
        similar_funcs, legacy_patterns, unused_imports
    )
    
    output_path = project_root / args.output
    output_path.write_text(report, encoding='utf-8')
    print(f"✅ Report saved to: {output_path}")
    
    # Print summary
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    print(f"Total modules: {len(modules)}")
    print(f"Total lines: {sum(m.lines for m in modules):,}")
    print(f"Circular dependencies: {len(cycles)}")
    print(f"Duplicate code blocks: {len(duplicates)}")
    print(f"Files with unused imports: {len(unused_imports)}")
    print(f"Legacy patterns found: {sum(len(v) for v in legacy_patterns.values())}")


if __name__ == '__main__':
    main()
