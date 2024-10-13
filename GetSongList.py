import aiohttp
import asyncio
import json
import re
import os


async def get_song_list(categoryID: str, origin=False):
    url = "https://i.y.qq.com/qzone-music/fcg-bin/fcg_ucc_getcdinfo_byids_cp.fcg"
    params = {
        "disstid": categoryID,
        "type": 1,
        "json": 1,
        "utf8": 1,
        "onlysong": 0,
        "nosign": 1,
    }

    headers = {
        "Referer": "https://y.qq.com/",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/94.0.4606.81 Safari/537.36",
    }

    async with aiohttp.ClientSession() as session:
        async with session.get(url, params=params, headers=headers) as response:
            response_text = await response.text()

            # 使用正则表达式提取JSON内容
            json_match = re.search(r"^\w+\((.*)\)$", response_text)
            if json_match:
                json_data = json_match.group(1)
            else:
                json_data = response_text

            try:
                data = json.loads(json_data)  # 尝试解析为JSON
            except json.JSONDecodeError as e:
                raise ValueError("Error parsing JSON") from e

            if origin:
                return data  # 直接返回请求返回的data
            else:
                # 处理并提取你想要的数据
                song_list = data.get("cdlist", [])[0].get("songlist", [])
                simplified_song_list = [
                    {"songname": song["songname"], "songmid": song["songmid"]}
                    for song in song_list
                ]
                return simplified_song_list


# 示例使用：
async def main():
    category_id = "123456"  # 你可以替换成实际的歌单ID
    song_list = await get_song_list(category_id, origin=False)

    # 使用 os 获取当前运行目录并构建文件路径
    current_directory = os.path.dirname(os.path.abspath(__file__))
    file_path = os.path.join(current_directory, "list.json")

    # 将结果写入本地文件list.json
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(song_list, f, ensure_ascii=False, indent=4)

    print("歌单已保存到 list.json 文件中")


# 运行异步任务
asyncio.run(main())
