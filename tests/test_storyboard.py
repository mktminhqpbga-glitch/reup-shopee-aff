import copy
import json
from pathlib import Path
import tempfile
import threading
import unittest

from automation import PipelineError
from storyboard import StoryMemory, build_storyboard, product_key
from story_fixtures import story_response

PRODUCT = {'title': 'Bình giữ nhiệt 500 ml', 'description': 'Dung tích 500 ml. Nắp có quai xách.',
           'image_urls': ['https://down-vn.img.susercontent.com/file/example'],
           'source_url': 'https://shopee.vn/Binh-i.123.456'}


class StoryboardTests(unittest.TestCase):
    def make(self, mutate=None, **kwargs):
        self.calls = []
        def ai(path, body, **options):
            phase = json.loads(body['messages'][1]['content'])['phase']
            self.calls.append(phase)
            result = story_response(body)
            if mutate:
                data = json.loads(result['choices'][0]['message']['content'])
                mutate(phase, data)
                result['choices'][0]['message']['content'] = json.dumps(data)
            return result
        return build_storyboard(PRODUCT, request=ai, **kwargs)

    def test_four_stages_and_scene_evidence(self):
        updates = []
        story = self.make(on_phase=lambda stage, value: updates.append((stage, value)))
        self.assertEqual(self.calls,['profile','director','writer','audit'])
        self.assertEqual(story['profile']['facts'][1]['quote'],'Nắp có quai xách.')
        self.assertEqual(story['scenes'][0]['narration'],story['plan']['hook'])
        self.assertTrue(story['review']['approved'])
        self.assertTrue(all(scene['visual_prompt'] and scene['fact_ids'] for scene in story['scenes']))
        self.assertIsNone(updates[0][1]['profile'])
        self.assertTrue(updates[-1][1]['review']['approved'])

    def test_invented_fact_is_rejected_before_writing(self):
        def mutate(phase, data):
            if phase=='profile': data['facts'][0]['quote']='Giữ lạnh suốt 48 giờ.'
        with self.assertRaises(PipelineError) as error:
            self.make(mutate)
        self.assertEqual(error.exception.code,'STORY_PROFILE_INVALID')
        self.assertEqual(self.calls,['profile'])

    def test_unknown_citation_cannot_reach_review(self):
        def mutate(phase, data):
            if phase=='writer': data['scenes'][1]['fact_ids']=['F999']
        with self.assertRaises(PipelineError) as error:
            self.make(mutate)
        self.assertEqual(error.exception.code,'STORY_SCENES_INVALID')
        self.assertEqual(self.calls,['profile','director','writer'])

    def test_reviewer_must_cover_every_scene(self):
        def mutate(phase, data):
            if phase=='audit': data['reviewed_scene_ids']=[1,2]
        with self.assertRaises(PipelineError) as error:
            self.make(mutate)
        self.assertEqual(error.exception.code,'STORY_AUDIT_INVALID')

    def test_review_rejection_is_saved_and_not_retried(self):
        updates=[]
        def mutate(phase, data):
            if phase=='audit':
                data.update(approved=False,issues=['Cảnh 2: thông tin chưa có nguồn.'])
        with self.assertRaises(PipelineError) as error:
            self.make(mutate,on_phase=lambda stage,value: updates.append(value))
        self.assertEqual(error.exception.code,'STORY_AUDIT_REJECTED')
        self.assertEqual(self.calls,['profile','director','writer','audit'])
        self.assertFalse(updates[-1]['review']['approved'])

    def test_history_changes_selected_angle(self):
        first=self.make()
        history=[{**first['plan'],'narration':'','title':PRODUCT['title']}]
        second=self.make(history=history)
        self.assertNotEqual(first['plan']['hook'],second['plan']['hook'])
        self.assertNotEqual(first['plan']['angle'],second['plan']['angle'])

    def test_director_rejects_title_substitution_before_writer(self):
        first=self.make()
        other_title='Bộ bàn ghế ngoài trời bằng gỗ'
        history=[{**first['plan'], 'title':other_title,
                  'hook':first['plan']['hook'].replace(PRODUCT['title'], other_title)}]
        second=self.make(history=history)
        self.assertNotEqual(second['plan']['hook'],first['plan']['hook'])
        self.assertEqual(second['plan']['angle'],'Soi chi tiết')

    def test_duplicate_reservation_is_atomic_between_workers(self):
        story=self.make()
        with tempfile.TemporaryDirectory() as directory:
            memory=StoryMemory(Path(directory)/'history.sqlite3')
            barrier=threading.Barrier(2)
            results=[]
            def reserve(job):
                barrier.wait()
                try:
                    memory.remember(job,PRODUCT,story)
                    results.append('accepted')
                except PipelineError as error:
                    results.append(error.code)
            threads=[threading.Thread(target=reserve,args=(str(i),)) for i in range(2)]
            for thread in threads: thread.start()
            for thread in threads: thread.join(5)
            self.assertEqual(sorted(results),['STORY_TOO_SIMILAR','accepted'])
            restored=StoryMemory(Path(directory)/'history.sqlite3')
            self.assertEqual(len(restored.history(PRODUCT)),1)

    def test_changing_only_product_name_is_not_a_new_script(self):
        first=self.make()
        other={**PRODUCT,'title':'Bình giữ nhiệt 1000 ml','source_url':'https://shopee.vn/product/123/999'}
        second=copy.deepcopy(first)
        for scene in second['scenes']:
            scene['narration']=scene['narration'].replace(PRODUCT['title'],other['title'])
        second['plan']['hook']=second['plan']['hook'].replace(PRODUCT['title'],other['title'])
        with tempfile.TemporaryDirectory() as directory:
            memory=StoryMemory(Path(directory)/'history.sqlite3')
            memory.remember('first',PRODUCT,first)
            with self.assertRaises(PipelineError) as error:
                memory.remember('second',other,second)
            self.assertEqual(error.exception.code,'STORY_TOO_SIMILAR')

    def test_tracking_urls_share_product_identity(self):
        self.assertEqual(product_key(PRODUCT),product_key({**PRODUCT,'source_url':'https://shopee.vn/product/123/456?tracking=another'}))
