"""In-memory doubles: never import Firebase/Streamlit application entrypoints."""
import ast
import copy
import hashlib
import json
from types import SimpleNamespace
from clinical_source import load, tree, execute
from services.patient_context import limpar_contexto_paciente, preparar_contexto_paciente, payload_do_paciente_ativo


class State(dict):
    def __getattr__(self, key):
        return self[key]
    def __setattr__(self, key, value):
        self[key] = value


class UI:
    def __init__(self, state=None):
        self.session_state = State(state or {})
        self.messages = []
    def caption(self, message):
        self.messages.append(message)


class MemoryDB:
    """Models document identity and full-field writes, not SDK/transaction behavior."""
    def __init__(self):
        self.records = {}
        self.writes = []
        self.timeout_after_add = False
        self.fail_writes = False
    def collection(self, name):
        return Collection(self, name)


class Collection:
    def __init__(self, db, name):
        self.db, self.name = db, name
    def document(self, doc_id):
        return Document(self.db, self.name, doc_id)
    def add(self, payload):
        doc = self.document(f'fake-{len(self.db.records)+1}')
        doc.set(payload)
        if self.db.timeout_after_add:
            self.db.timeout_after_add = False
            raise TimeoutError('Synthetic lost acknowledgement')
        return None, doc


class Document:
    def __init__(self, db, collection, doc_id):
        self.db, self.collection, self.id = db, collection, doc_id
    def set(self, payload, merge=False):
        if self.db.fail_writes:
            raise ConnectionError('Synthetic write failure')
        key = (self.collection, self.id)
        value = copy.deepcopy(self.db.records.get(key, {})) if merge else {}
        value.update(copy.deepcopy(payload))
        self.db.records[key] = value
        self.db.writes.append((key, copy.deepcopy(payload)))
    def get(self):
        value = copy.deepcopy(self.db.records.get((self.collection, self.id)))
        return SimpleNamespace(exists=value is not None, to_dict=lambda: value)


def isolated(filename, ui=None, db=None):
    module = load(filename)
    # Each load has its own function globals; never instantiate the real adapter.
    for value in vars(module).values():
        if callable(value) and hasattr(value, '__globals__'):
            value.__globals__.update(st=ui or UI(), db=db or MemoryDB(),
                                     json=json, hashlib=hashlib,
                                     limpar_contexto_paciente=limpar_contexto_paciente,
                                     preparar_contexto_paciente=preparar_contexto_paciente,
                                     payload_do_paciente_ativo=payload_do_paciente_ativo,
                                     invalidar_cache=lambda *args: None)
    return module


def adapter_class():
    nodes = [n for n in tree('firebase_client.py').body if isinstance(n, ast.ClassDef) and n.name == 'FirebaseAdapter']
    assert len(nodes) == 1
    ns = {}
    execute(nodes, ns, 'firebase_client.py')
    return ns['FirebaseAdapter']


def panel_longitudinal(frame):
    """Execute original longitudinal preprocessing loop, stopping before UI."""
    source = tree('modulo_painel.py')
    render = next(n for n in source.body if isinstance(n, ast.FunctionDef) and n.name == 'render')
    start = next(i for i,n in enumerate(render.body) if isinstance(n, ast.Assign) and any(isinstance(t,ast.Subscript) and ast.unparse(t)=="df_p['Data_dt']" for t in n.targets))
    end = next(i for i,n in enumerate(render.body) if isinstance(n, ast.Assign) and any(isinstance(t,ast.Subscript) and ast.unparse(t)=="df_p['LSI']" for t in n.targets))
    assert end > start
    panel = load('modulo_painel.py')
    ns = vars(panel).copy()
    ns['df_p'] = frame.copy(deep=True)
    execute(render.body[start:end+1], ns, 'modulo_painel.py')
    return ns['df_p']
