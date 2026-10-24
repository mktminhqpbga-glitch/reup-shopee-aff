"""Deterministic service fixtures; these do not test real model quality."""
import copy
import json


def story_response(body):
    data = json.loads(body['messages'][1]['content'])
    phase = data['phase']
    if phase == 'profile':
        result = {'category': 'Đồ dùng cá nhân', 'audience': 'Người cần đồ dùng mang theo',
                  'need': 'Chuẩn bị đồ dùng phù hợp', 'facts': [
                      {'source': 'description', 'quote': 'Nắp có quai xách.'}],
                  'unknowns': ['Thời gian giữ nhiệt thực tế']}
    elif phase == 'director':
        title = data['profile']['facts'][0]['quote']
        result = {'candidates': [
            {'angle': 'Đồ dùng mang theo', 'audience': 'Người đi làm', 'situation': 'Chuẩn bị túi đi làm',
             'hook': f'Trong túi đi làm của bạn có {title} chưa?', 'rationale': 'Giới thiệu theo chi tiết có quai trong nguồn.',
             'fact_ids': ['F0', 'F1'], 'relevance': 9, 'visual_fit': 9},
            {'angle': 'Soi chi tiết', 'audience': 'Người mua', 'situation': 'Xem chi tiết trên bàn',
             'hook': 'Bạn thường kiểm tra phần nắp trước khi mua bình không?', 'rationale': 'Nguồn có mô tả nắp.',
             'fact_ids': ['F1'], 'relevance': 8, 'visual_fit': 8},
            {'angle': 'Danh sách cần kiểm tra', 'audience': 'Người mua', 'situation': 'Tìm hiểu thông số',
             'hook': 'Có những thông tin nào bạn nên xem thêm trước khi đặt hàng?', 'rationale': 'Không suy diễn dữ kiện còn thiếu.',
             'fact_ids': ['F0'], 'relevance': 7, 'visual_fit': 8}]}
    elif phase == 'writer':
        result = {'scenes': [
            {'kind': 'hook', 'narration': data['plan']['hook'], 'fact_ids': ['F0'],
             'visual_prompt': 'Cận cảnh ảnh tham chiếu trên bàn, giữ nguyên sản phẩm.', 'image_index': 0, 'estimated_seconds': 6},
            {'kind': 'detail', 'narration': 'Theo mô tả sản phẩm, nắp có quai xách.', 'fact_ids': ['F1'],
             'visual_prompt': 'Hiển thị toàn bộ ảnh tham chiếu. Không tự tạo thêm chi tiết.', 'image_index': 0, 'estimated_seconds': 6},
            {'kind': 'cta', 'narration': 'Bạn xem thông tin tại link trong bài nhé. Có liên kết tiếp thị.', 'fact_ids': ['F0'],
             'visual_prompt': 'Khung kết thúc với ảnh gốc sản phẩm.', 'image_index': 0, 'estimated_seconds': 6}]}
    elif phase == 'audit':
        result = {'approved': True, 'reviewed_scene_ids': [1, 2, 3], 'issues': [],
                  'summary': 'Fixture: kiểm tra đủ ba cảnh.'}
    else:
        raise AssertionError('Unexpected phase: ' + phase)
    return {'choices': [{'message': {'content': json.dumps(copy.deepcopy(result), ensure_ascii=False)}}]}
