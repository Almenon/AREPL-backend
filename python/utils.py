import ast
from copy import deepcopy

oldSavedLines = []
startingLocals = {}

# public cache var for user to store their data between runs
areplStore = None

def get_starting_locals():
    starting_locals_copy = deepcopy(startingLocals)
    starting_locals_copy['areplStore'] = areplStore
    return starting_locals_copy


def exec_saved(savedLines):
    savedLocals = get_starting_locals()
    try:
        exec(savedLines, savedLocals)
    except Exception:
        errorMsg = traceback.format_exc()
        raise UserError(errorMsg, savedLocals)

    # deepcopy cant handle imported modules, so remove them
    savedLocals = {k:v for k,v in savedLocals.items() if str(type(v)) != "<class 'module'>"}

    return savedLocals


def get_eval_locals(savedLines):
    """
    If savedLines is changed, rexecutes saved lines and returns resulting local variables.
    If savedLines is unchanged, returns the saved locals.
    If savedLines is empty, simply returns the original startingLocals.
    """
    global oldSavedLines
    global savedLocals

    # "saved" code we only ever run once and save locals, vs. codeToExec which we exec as the user types
    # although if saved code has changed we need to re-run it
    if savedLines != oldSavedLines:
        savedLocals = exec_saved(savedLines)
        oldSavedLines = savedLines

    if savedLines != "":
        return deepcopy(savedLocals)
    else:
        return get_starting_locals()


def get_imports(parsedText, text):
    """
    :param parsedText: the result of ast.parse(text)
    :returns: empty string if no imports, otherwise string containing all imports
    """

    child_nodes = [l for l in ast.iter_child_nodes(parsedText)]

    imports = []
    savedCode = text.split('\n')
    for node in child_nodes:
        if isinstance(node, ast.Import) or isinstance(node, ast.ImportFrom):
            importLine = savedCode[node.lineno - 1]
            imports.append(importLine)

    imports = '\n'.join(imports)
    return imports


def copy_saved_imports_to_exec(codeToExec, savedLines):
    """
    copies imports in savedLines to the top of codeToExec.
    If savedLines is empty this function does nothing.
    :raises: SyntaxError if err in savedLines
    """
    if savedLines.strip() != "":
        try:
            savedCodeAST = ast.parse(savedLines)
        except SyntaxError:
            errorMsg = traceback.format_exc()
            raise UserError(errorMsg)

        imports = get_imports(savedCodeAST, savedLines)
        codeToExec = imports + '\n' + codeToExec

        # to make sure line # in errors is right we need to pad codeToExec with newlines
        numLinesToAdd = len(savedLines.split('\n')) - len(imports.split('\n'))
        for i in range(numLinesToAdd):
            codeToExec = '\n' + codeToExec

    return codeToExec

