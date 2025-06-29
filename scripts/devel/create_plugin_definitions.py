#!/usr/bin/python3

import os
import ast
import sys
import glob

class SafeDictExtractor(ast.NodeVisitor):
    def __init__(self, variable_name):
        self.variable_name = variable_name
        self.result = None

    def visit_Assign(self, node):
        for target in node.targets:
            if isinstance(target, ast.Name) and target.id == self.variable_name:
                self.result = self._safe_eval(node.value)

    def _safe_eval(self, node):
        if isinstance(node, ast.Dict):
            return {
                self._safe_eval(k): self._safe_eval(v)
                for k, v in zip(node.keys, node.values)
            }
        elif isinstance(node, ast.List):
            return [self._safe_eval(elt) for elt in node.elts]
        elif isinstance(node, ast.Constant):  # str, int, float, etc.
            return node.value
        elif isinstance(node, ast.Call):
            # Handle gettext-style calls like _('Some text')
            if isinstance(node.func, ast.Name) and node.func.id == "_":
                if node.args and isinstance(node.args[0], ast.Constant):
                    return node.args[0].value
        raise ValueError(f"Unsupported expression: {ast.dump(node)}")

def extract_variable_from_python_module(filepath, variable_name):
    with open(filepath, "r") as f:
        tree = ast.parse(f.read(), filename=filepath)
    extractor = SafeDictExtractor(variable_name)
    extractor.visit(tree)
    if extractor.result is None:
        # ~ raise ValueError(f"Variable '{variable_name}' not found.")
        return None
    return extractor.result

if __name__ == '__main__':
    if len(sys.argv) < 2:
        exit("Error. You must provide the root directory where all your plugins reside")

    try:
        plugins_path = os.path.abspath(sys.argv[1])
        if os.path.exists(plugins_path):
            python_modules = glob.glob(os.path.join(plugins_path, '*', '*.py'))
            for python_module in python_modules:
                plugin_path = os.path.dirname(python_module)
                plugin_file = os.path.basename(python_module)
                plugin_info = extract_variable_from_python_module(python_module, 'plugin_info')
                if plugin_info is not None:
                    plugin_def = os.path.join(plugin_path, plugin_file.replace('.py', '.plugin'))
                    with open(plugin_def, 'w') as fdef:
                        definition = "[Plugin]\n"
                        for key in plugin_info:
                            definition += f'{key}={plugin_info[key]}\n'
                        fdef.write(definition)
                        print(f"Plugin definition for {os.path.basename(plugin_path)} > {plugin_file} created successfully ({plugin_def})")
                else:
                    print(f"Error: Module {os.path.basename(python_module)} doesn't contain the plugin info dictionary")
        else:
            print(f"Error: '{plugins_path}' do not exist")
    except Exception as error:
        raise
