import csv
import io
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import modelopredictJD as model


class LotteryFeaturesTest(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.original_csv = model.CSV_PATH
        self.original_historic = model.HISTORIC_PATH
        model.CSV_PATH = str(Path(self.directory.name) / 'Melate.csv')
        model.HISTORIC_PATH = str(Path(self.directory.name) / 'Historic.csv')
        with open(model.CSV_PATH, 'w', newline='', encoding='utf-8') as handle:
            writer = csv.writer(handle)
            writer.writerow(model.CSV_COLUMNS)
            writer.writerow([40, 9, 2, 3, 4, 5, 6, 7, 8, 100, '01/10/2026'])
            writer.writerow([40, 100, 11, 13, 17, 20, 24, 30, 31, 200, '04/10/2026'])
        model.app.config['TESTING'] = True
        self.client = model.app.test_client()

    def tearDown(self):
        model.CSV_PATH = self.original_csv
        model.HISTORIC_PATH = self.original_historic
        self.directory.cleanup()

    def test_random_has_six_main_and_unique_additional(self):
        response = self.client.get('/api/random')
        self.assertEqual(response.status_code, 200)
        for suggestion in response.json['suggestions']:
            self.assertEqual(len(suggestion['main']), 6)
            self.assertEqual(len(set(suggestion['suggestion'])), 7)
            self.assertFalse(set(suggestion['suggestion']) & {11, 13, 17, 20, 24, 30, 31})

    def test_prediction_and_random_respect_each_type_quota(self):
        for primes in range(6):
            params = f'?primos={primes}&compuestos={5 - primes}'
            prediction = self.client.get('/api/predecir/50' + params)
            self.assertEqual(prediction.status_code, 200)
            self.assertEqual(sum(model.es_primo(row['numero']) for row in prediction.json), primes)
            self.assertEqual(sum(model.es_compuesto(row['numero']) for row in prediction.json), 5 - primes)
            random = self.client.get('/api/random' + params)
            self.assertEqual(random.status_code, 200)
            for suggestion in random.json['suggestions']:
                self.assertEqual(len(suggestion['main']), 5)
                self.assertEqual(sum(model.es_primo(n) for n in suggestion['main']), primes)

    def test_invalid_quotas_return_json(self):
        for params in ['?primos=4&compuestos=4', '?primos=x', '?primos=-1&compuestos=6']:
            for endpoint in ['/api/random', '/api/predecir/50']:
                response = self.client.get(endpoint + params)
                self.assertEqual(response.status_code, 400)
                self.assertIn('error', response.json)

    def test_manual_contest_uses_numeric_max_and_keeps_missing_additional(self):
        response = self.client.post('/api/add_row', json={'numeros': [2, 3, 4, 5, 6, 7], 'fecha': '07/10/2026'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json['added']['CONCURSO'], 101)
        preview = self.client.get('/api/preview').json
        self.assertEqual(preview[0]['CONCURSO'], 101)
        self.assertIsNone(preview[0]['R7'])
        self.assertEqual(self.client.get('/api/random').status_code, 200)

    def test_invalid_manual_input_never_writes(self):
        before = Path(model.CSV_PATH).read_bytes()
        payloads = [
            {'numeros': [1, 2, 3, 4, 5, 57]},
            {'numeros': [1, 2, 3, 4, 5, 5]},
            {'numeros': [1.5, 2, 3, 4, 5, 6]},
            {'numeros': [True, 2, 3, 4, 5, 6]},
            {'numeros': [1, 2, 3, 4, 5, 6], 'fecha': '31/02/2026'},
            {'numeros': [1, 2, 3, 4, 5, 6], 'concurso': 100},
            {'numeros': [1, 2, 3, 4, 5, 6], 'bolsa': -1},
            [],
        ]
        for payload in payloads:
            self.assertEqual(self.client.post('/api/add_row', json=payload).status_code, 400)
            self.assertEqual(Path(model.CSV_PATH).read_bytes(), before)

    def test_bulk_one_hundred_rows_get_unique_contests(self):
        response = self.client.post('/api/add_rows', json={'lines': ['2,3,4,5,6,7,8 — 07/10/2026'] * 100})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json['added'], 100)
        frame = model.cargar_datos()
        self.assertEqual(len(frame), 102)
        self.assertEqual(set(frame.CONCURSO), {9} | set(range(100, 201)))

    def test_invalid_bulk_is_rejected_without_partial_write(self):
        before = Path(model.CSV_PATH).read_bytes()
        for lines in [
            ['2,3,4,5,6,7 — 07/10/2026', '2,3,4,5,6,6 — 08/10/2026'],
            ['2,3,4,5,6,7 — 07/10/2026'] * 101,
            ['2,3,4,5,6,7 — invalid'],
        ]:
            response = self.client.post('/api/add_rows', json={'lines': lines})
            self.assertEqual(response.status_code, 400)
            self.assertEqual(Path(model.CSV_PATH).read_bytes(), before)

    def test_concurrent_additions_do_not_reuse_contest_ids(self):
        def add(_):
            with model.app.test_client() as client:
                return client.post('/api/add_row', json={'numeros': [2, 3, 4, 5, 6, 7], 'fecha': '07/10/2026'})
        with ThreadPoolExecutor(max_workers=4) as executor:
            responses = list(executor.map(add, range(8)))
        self.assertTrue(all(response.status_code == 200 for response in responses))
        self.assertEqual({response.json['added']['CONCURSO'] for response in responses}, set(range(101, 109)))

    def test_export_and_sync_include_new_draw_without_changing_source(self):
        self.client.post('/api/add_row', json={'numeros': [2, 3, 4, 5, 6, 7], 'fecha': '07/10/2026'})
        before = Path(model.CSV_PATH).read_bytes()
        snapshot = self.client.get('/api/historic_csv').get_data(as_text=True)
        response = self.client.post('/api/sync_localstorage_csv', json={'csv': snapshot})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json['rows'], 3)
        self.assertEqual(Path(model.HISTORIC_PATH).read_text(), snapshot)
        self.assertEqual(Path(model.CSV_PATH).read_bytes(), before)
        self.assertIn('101', [row['CONCURSO'] for row in csv.DictReader(io.StringIO(snapshot))])

    def test_invalid_sync_preserves_previous_mirror(self):
        Path(model.HISTORIC_PATH).write_text('previous snapshot')
        for payload in [{'csv': 'invalid'}, {'csv': ','.join(model.CSV_COLUMNS)}, []]:
            self.assertEqual(self.client.post('/api/sync_localstorage_csv', json=payload).status_code, 400)
            self.assertEqual(Path(model.HISTORIC_PATH).read_text(), 'previous snapshot')

    def test_out_of_range_legacy_draw_is_ignored(self):
        with open(model.CSV_PATH, 'a', newline='') as handle:
            csv.writer(handle).writerow([40, 101, 3, 718, 35, 36, 52, 46, '', 0, '07/10/2026'])
        self.assertEqual(len(model.cargar_datos()), 2)
        self.assertEqual(self.client.get('/api/random').status_code, 200)
        snapshot = self.client.get('/api/historic_csv').get_data(as_text=True)
        self.assertEqual(self.client.post('/api/sync_localstorage_csv', json={'csv': snapshot}).status_code, 200)

    def test_agent_respects_type_quotas_and_gives_explanations(self):
        for primes in range(7):
            response = self.client.post('/api/agente', json={'primos': primes, 'compuestos': 6 - primes})
            self.assertEqual(response.status_code, 200)
            result = response.json
            self.assertEqual(len(result['primos']), primes)
            self.assertEqual(len(result['compuestos']), 6 - primes)
            self.assertEqual(len(set(result['suggestion'])), 7)
            self.assertEqual({row['numero'] for row in result['explicaciones']}, set(result['main']))

    def test_agent_uses_custom_sets(self):
        response = self.client.post('/api/agente', json={
            'pool_primos': [2, 3, 5], 'pool_compuestos': [4, 6, 8],
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json['main'], [2, 3, 4, 5, 6, 8])

    def test_agent_can_exclude_latest_draw(self):
        response = self.client.post('/api/agente', json={'excluir_ultimo': True})
        self.assertEqual(response.status_code, 200)
        self.assertFalse(set(response.json['suggestion']) & {11, 13, 17, 20, 24, 30, 31})

    def test_agent_rejects_wrong_types_and_insufficient_candidates(self):
        for payload in [
            {'pool_primos': [4, 6, 8]}, {'pool_primos': [2]},
            {'pool_compuestos': [1, 4, 6]}, {'pool_primos': '2,3,5'},
            {'primos': 4, 'compuestos': 4}, {'primos': 3.5},
            {'excluir_ultimo': 'false'}, [],
        ]:
            response = self.client.post('/api/agente', json=payload)
            self.assertEqual(response.status_code, 400)
            self.assertIn('error', response.json)


if __name__ == '__main__':
    unittest.main()
