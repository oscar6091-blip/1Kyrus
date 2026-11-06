"""Check this plan pack's consistency. This does not test the future web app.

Uses only the Python standard library. The schema checker below implements
the JSON Schema keywords used by this pack; it is not a general validator.
"""
from pathlib import Path
import ast
import hashlib
import json
import math
import os
import re
import sqlite3
import zipfile
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]


def load(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def resolve(ref, document):
    file, _, fragment = ref.partition('#')
    target = (document.parent / file).resolve() if file else document
    value = load(target)
    for key in fragment.lstrip('/').split('/') if fragment else []:
        value = value[key.replace('~1', '/').replace('~0', '~')]
    return value, target


def validate(value, schema, document, path='$'):
    errors = []
    if '$ref' in schema:
        child, target = resolve(schema['$ref'], document)
        return validate(value, child, target, path)
    for name in ['anyOf', 'oneOf']:
        if name in schema:
            alternatives = [validate(value, s, document, path) for s in schema[name]]
            valid = sum(not e for e in alternatives)
            if (name == 'anyOf' and valid == 0) or (name == 'oneOf' and valid != 1):
                errors.append(f'{path}: {name} mismatch')
            return errors
    if 'const' in schema and (type(value) is not type(schema['const']) or value != schema['const']):
        errors.append(f'{path}: wrong const')
    if 'enum' in schema and not any(type(value) is type(x) and value == x for x in schema['enum']):
        errors.append(f'{path}: wrong enum')
    kind = schema.get('type')
    types = {
        'object': lambda x: isinstance(x, dict),
        'array': lambda x: isinstance(x, list),
        'string': lambda x: isinstance(x, str),
        'integer': lambda x: isinstance(x, int) and not isinstance(x, bool),
        'number': lambda x: isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(x),
        'boolean': lambda x: isinstance(x, bool),
        'null': lambda x: x is None,
    }
    if kind and not types[kind](value):
        return errors + [f'{path}: expected {kind}']
    if kind == 'object':
        properties = schema.get('properties', {})
        for key in schema.get('required', []):
            if key not in value:
                errors.append(f'{path}.{key}: missing')
        if len(value) < schema.get('minProperties', 0):
            errors.append(f'{path}: too few properties')
        for key, item in value.items():
            if key in properties:
                errors += validate(item, properties[key], document, path + '.' + key)
            else:
                extra = schema.get('additionalProperties', True)
                if extra is False:
                    errors.append(f'{path}.{key}: extra property')
                elif isinstance(extra, dict):
                    errors += validate(item, extra, document, path + '.' + key)
    elif kind == 'array':
        if len(value) < schema.get('minItems', 0) or len(value) > schema.get('maxItems', float('inf')):
            errors.append(f'{path}: array length')
        for i, item in enumerate(value):
            errors += validate(item, schema.get('items', {}), document, f'{path}[{i}]')
    elif kind == 'string':
        if len(value) < schema.get('minLength', 0) or len(value) > schema.get('maxLength', float('inf')):
            errors.append(f'{path}: string length')
        if 'pattern' in schema and not re.search(schema['pattern'], value):
            errors.append(f'{path}: string pattern')
    elif kind in ('integer', 'number'):
        if value < schema.get('minimum', -float('inf')) or value > schema.get('maximum', float('inf')):
            errors.append(f'{path}: numeric range')
    return errors


def walk_refs(node, document):
    if isinstance(node, dict):
        if '$ref' in node:
            resolve(node['$ref'], document)
        for value in node.values():
            walk_refs(value, document)
    elif isinstance(node, list):
        for item in node:
            walk_refs(item, document)


def original_ssrd_content(path):
    ns = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
    with zipfile.ZipFile(path) as archive:
        body = ET.fromstring(archive.read('word/document.xml')).find('w:body', ns)
    records, blocks = [], []
    section, table_index = '', 0
    for node in body:
        if node.tag.endswith('}p'):
            text = ''.join(t.text or '' for t in node.findall('.//w:t', ns))
            if not text.strip():
                continue
            if re.match(r'^(?:[1-7](?:\.\d+)* [A-Za-z]|A\.[IVX]+ )', text):
                section = text
            if section:
                blocks.append({'kind': 'paragraph', 'section': section, 'text': text})
        elif node.tag.endswith('}tbl'):
            table_index += 1
            rows = []
            for row in node.findall('w:tr', ns):
                rows.append(['\n'.join(''.join(t.text or '' for t in p.findall('.//w:t', ns))
                                      for p in cell.findall('w:p', ns))
                             for cell in row.findall('w:tc', ns)])
            if rows and len(rows[0]) == 2 and rows[0][0] in {
                    'Project requirement:', 'Requirement:', 'Level of service:', 'Evolution requirement:'}:
                match = re.match(r'(PR|RQ|ONRQ|SIR|LOR|LOS|CR)-\d+\b', rows[0][1])
                records.append((match.group().replace('LOS-', 'LOR-'),
                                [{'label': a, 'value': b} for a, b in rows]))
            elif section:
                blocks.append({'kind': 'table', 'section': section,
                               'document_table_index': table_index, 'rows': rows})
    return records, blocks


def run():
    static_dirs = {'contracts','fixtures','prompts','reference_experiment','sources','scripts'}
    all_files = []
    for parent, dirs, names in os.walk(ROOT):
        dirs[:] = [d for d in dirs if d not in {'.venv','node_modules','__pycache__','.git'} and (Path(parent) != ROOT or d in static_dirs)]
        all_files.extend(Path(parent) / n for n in names)
    all_files.sort()
    json_files = [p for p in all_files if p.suffix == '.json']
    for p in json_files:
        load(p)
    contracts = ROOT / 'contracts'
    for p in contracts.glob('*.json'):
        walk_refs(load(p), p)
    source = load(ROOT / 'sources/requirements.all.json')['requirements']
    selected = load(ROOT / 'requirements.selected.json')['requirements']
    scope = load(ROOT / 'scope.json')
    assert len(source) == 55
    assert len({r['id'] for r in source}) == 55
    assert sum(len(r['fields']) for r in source) == 478
    assert sum(f['value'] == '' for r in source for f in r['fields']) == 26
    index = {r['id']: r for r in source}
    assert len(selected) == 36
    assert {r['id'] for r in selected} == set(scope['must'])
    assert set(scope['must']).isdisjoint({r['id'] for r in scope['deferred']})
    assert set(scope['must']) | {r['id'] for r in scope['deferred']} == set(index)
    for r in selected:
        assert r['fields'] == index[r['id']]['fields']
        assert all(isinstance(f['label'], str) and isinstance(f['value'], str) for f in r['fields'])
    assert index['LOR-2']['original_id'] == 'LOS-2'
    assert index['LOR-10']['original_id'] == 'LOS-10'
    cases = load(ROOT / 'acceptance.cases.json')['cases']
    case_ids = {c['id'] for c in cases}
    assert len(cases) == 20 and len(case_ids) == 20
    for r in selected:
        assert r['prototype']['acceptance_ids'], r['id']
        assert set(r['prototype']['acceptance_ids']) <= case_ids
    for c in cases:
        assert set(c['requirements']) <= set(scope['must'])

    context = load(ROOT / 'sources/ssrd_context.json')
    assert len(context['original_files']) == 2
    for item in context['original_files']:
        assert hashlib.sha256((ROOT / 'sources' / item['path']).read_bytes()).hexdigest() == item['sha256']
    original_records, original_blocks = original_ssrd_content(ROOT / 'sources/original/SSRD_v0.1.docx')
    assert len(original_records) == 55
    for (source_id, fields), record in zip(original_records, source):
        assert source_id == record['id'] and fields == record['fields'], source_id
    assert original_blocks == context['non_requirement_blocks']
    assert {r['화면 ID'] for r in context['ui_definitions']} == {f'UI-{n:02}' for n in range(1, 11)}
    assert {r['ID'] for r in context['customer_assumptions']} == {f'A-{n}' for n in range(1, 8)}
    assert all(r['validation_status'] == 'not_validated_in_supplied_sources' for r in context['customer_assumptions'])
    assert len(context['external_upload_original']['fields']) == 8
    assert json.loads(context['external_upload_original']['json_example_verbatim']) == context['external_upload_original']['json_example']
    resolutions = scope['source_review_resolution']
    assert {r['id'] for r in resolutions} == {f'N-{n:02}' for n in range(1, 10)}
    for item in resolutions:
        assert all((ROOT / p).is_file() for p in item['files']), item['id']
        assert set(item['acceptance_ids']) <= case_ids
    baseline = {r['id']: r['value'] for r in scope['prototype_baseline']['settings']}
    assert baseline == {'database': 'SQLite', 'brief_update': 'S1_approval_only',
                        'back_behavior': 'record_and_navigate_only', 'paper_output': 'English Markdown'}
    assert scope['upload_format']['accepts_original_ssrd_example_unchanged'] is False

    artifact_file = contracts / 'artifacts.schema.json'
    artifact_schema = load(artifact_file)
    payloads = {}
    for n in range(1, 7):
        p = load(ROOT / f'fixtures/stages/s{n}.json')
        errors = validate(p, artifact_schema, artifact_file)
        assert not errors, (n, errors)
        assert p['stage_no'] == n
        payloads[n] = p
    upload_file = contracts / 'upload.schema.json'
    upload_schema = load(upload_file)
    valid = load(ROOT / 'fixtures/experiment_result.valid.json')
    bad = load(ROOT / 'fixtures/experiment_result.invalid.json')
    assert not validate(valid, upload_schema, upload_file)
    assert validate(bad, upload_schema, upload_file)
    source_example_errors = validate(context['external_upload_original']['json_example'], upload_schema, upload_file)
    assert set(source_example_errors) == {'$.schema_version: missing', '$.data_origin: missing', '$.metrics[0].unit: missing'}
    assert valid['data_origin'] == 'measured'
    plan = payloads[3]['content']['experiments'][0]
    assert plan['id'] == valid['experiment_id']
    assert set(plan['metric_names']) <= {m['name'] for m in valid['metrics']}
    assert len({(m['name'], m['split'], m.get('step')) for m in valid['metrics']}) == len(valid['metrics'])
    expected = load(ROOT / 'fixtures/expected_reference_metrics.json')
    assert expected['metrics'] == valid['metrics']
    assert valid['metrics'][0]['value'] == valid['metrics'][2]['value']
    assert len(valid['config']['fit_warnings']) == 2
    assert payloads[5]['content']['hypothesis_verdicts'][0]['verdict'] == 'inconclusive'
    hypothesis_ids = {h['id'] for h in payloads[1]['content']['brief']['hypotheses']}
    covered = {h for exp in payloads[3]['content']['experiments'] for h in exp['hypothesis_ids']}
    assert covered == hypothesis_ids
    assert all(len(exp['hypothesis_ids']) == len(set(exp['hypothesis_ids'])) for exp in payloads[3]['content']['experiments'])
    assert '## Ablation 계획\n' in payloads[3]['content']['body_md']
    verdicts = payloads[5]['content']['hypothesis_verdicts']
    assert {v['hypothesis_id'] for v in verdicts} == hypothesis_ids and len(verdicts) == len(hypothesis_ids)
    train_path = ROOT / 'reference_experiment/train.py'
    assert hashlib.sha256(train_path.read_bytes()).hexdigest() == valid['code_version']
    s4files = {f['path']: f['content'] for f in payloads[4]['content']['files']}
    assert s4files['train.py'] == train_path.read_text()
    ast.parse(s4files['train.py'])
    references = load(ROOT / 'fixtures/references.snapshot.json')['references']
    domain_file = contracts / 'domain.schema.json'
    domain = load(domain_file)
    for r in references:
        assert not validate(r, domain['$defs']['ReferenceSnapshot'], domain_file)
    ref_ids = {r['id'] for r in references}
    metric_ids = {f'm{i}' for i in range(len(valid['metrics']))}
    for n, p in payloads.items():
        serialized = json.dumps(p, ensure_ascii=False)
        assert set(re.findall(r'\{\{cite:([^}]+)\}\}', serialized)) <= ref_ids
        assert set(re.findall(r'\{\{metric:([^}]+)\}\}', serialized)) <= (metric_ids if n in (5, 6) else set())
        for item in p['rationale']:
            for key in item['evidence_refs']:
                prefix, _, key_id = key.partition(':')
                assert (prefix == 'ref' and key_id in ref_ids) or (prefix == 'metric' and key_id in metric_ids)
    keys = [s['key'] for s in payloads[6]['content']['sections']]
    assert keys == ['abstract','introduction','related_work','methods','experiments','conclusion']

    api = load(contracts / 'api.openapi.json')
    operations = [v['operationId'] for path in api['paths'].values() for v in path.values()]
    assert len(operations) == 16 and len(set(operations)) == 16
    states = load(contracts / 'workflow.json')['stage_states']
    for transition in load(contracts / 'workflow.json')['transitions']:
        assert set(transition['from']) <= set(states)
        assert transition['to'] in states + ['unchanged']

    db = sqlite3.connect(':memory:')
    db.executescript((contracts / 'database.sql').read_text())
    tables = {r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert tables == {'projects','stages','artifact_versions','jobs','decisions','experiment_runs'}
    db.execute("INSERT INTO projects VALUES ('p','name','idea','demo',NULL,'now','now')")
    db.execute("INSERT INTO stages VALUES ('p',1,'pending',NULL,NULL)")
    row = ('j1','r1','run:p:1:r1','sha','p',1,'queued','{}',None,'{}',None,'now',None,None)
    db.execute('INSERT INTO jobs VALUES (' + ','.join('?' * 14) + ')', row)
    try:
        row2 = ('j2','r2','run:p:1:r2','sha','p',1,'running','{}',None,'{}',None,'now',None,None)
        db.execute('INSERT INTO jobs VALUES (' + ','.join('?' * 14) + ')', row2)
    except sqlite3.IntegrityError:
        pass
    else:
        raise AssertionError('Active job unique index is missing')
    db.close()

    required = ['CLAUDE.md','SOURCE_COVERAGE.md','LLM_DATA_POLICY.md','architecture.md','implementation_plan.md',
                'acceptance.md','prompts/stage_prompts.md','.env.example','IMPLEMENTATION_STATUS.md']
    assert all((ROOT / p).is_file() for p in required)
    for p in [p for p in all_files if p.suffix == '.md']:
        assert p.read_text().count('```') % 2 == 0, p
    for p in [p for p in all_files if p.suffix == '.py']:
        ast.parse(p.read_text())
    result = {
        'result': 'PASS', 'source_requirements': 55, 'source_fields': 478,
        'selected_requirements': 36, 'deferred_requirements': 19,
        'artifact_fixtures': 6, 'references': len(references), 'measured_metrics': 4,
        'api_operations': len(operations), 'acceptance_cases': len(cases),
        'database_tables': len(tables),
        'original_documents': len(context['original_files']), 'source_context_blocks': len(original_blocks),
        'ui_definitions': len(context['ui_definitions']), 'customer_assumptions': len(context['customer_assumptions']),
        'source_review_items': len(resolutions),
        'original_upload_compatibility': 'Explicitly unsupported; original example rejected at three documented missing fields.',
        'scope_of_check': 'Source fidelity, plan consistency, supported schema keywords, references, fixtures, measured result linkage, SQLite DDL. The web application and provider policy are not verified here.',
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    run()
