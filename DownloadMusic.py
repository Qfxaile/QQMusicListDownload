import os, json, aiohttp, asyncio, re
from pydub import AudioSegment


# 获取当前目录及相关路径
current_directory = os.path.dirname(os.path.abspath(__file__))
music_list_file = os.path.join(current_directory, "list.json")
music_data_dir = os.path.join(current_directory, "music")


# 初始化函数，创建 music 文件夹
def init():
    if not os.path.exists(music_data_dir):
        os.mkdir(music_data_dir)


# 获取音乐列表
def get_music_list(path: str) -> list:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


# 异步获取音乐下载链接
async def get_music_info(session, songmid: str, uin=None, skey=None, n=1, br=4) -> dict:
    url = "https://api.xingzhige.com/API/QQmusicVIP/"
    params = {
        "mid": songmid,
        "n": n,
        "br": br,
    }

    # 如果提供了 uin 和 skey，则将其加入参数中
    if uin:
        params["uin"] = uin
    if skey:
        params["skey"] = skey

    # 异步请求获取下载链接
    async with session.get(url, params=params) as response:
        if response.status == 200:
            try:
                response_data = await response.json()
                # 确保返回的 code 是 200，且获取到歌曲的 src 链接
                if response_data.get("code") == 0:
                    song_info = response_data.get("data", {})
                    return {
                        "src": song_info.get("src"),
                        "songname": song_info.get("songname"),
                        "artist": song_info.get("name"),
                    }
                else:
                    print(f"获取音乐信息失败，原因：{response_data.get('msg')}")
                    return {}
            except aiohttp.ContentTypeError:
                raise ValueError("无法解析 JSON 响应。")
        else:
            raise ValueError(f"获取音乐信息失败，状态码：{response.status}")


# 异步转换音频格式
async def convert_to_mp3(file_name: str, original_path: str, mp3_path: str):
    print(f"正在转换 {file_name} 为 MP3...")
    audio = AudioSegment.from_file(original_path)  # 读取下载的 m4a 文件
    audio.export(mp3_path, format="mp3")  # 转换为 mp3 格式
    print(f"{file_name}.mp3 转换成功，保存到 {mp3_path}")
    os.remove(original_path)  # 删除原始文件
    print(f"原始文件 {original_path} 已删除")
    
    
# 异步下载音乐
async def download_music(session, song_name: str, songmid: str, semaphore: asyncio.Semaphore):
    async with semaphore:  # 使用信号量来限制并发数量
        music_info = await get_music_info(session, songmid)

        if music_info.get("src"):
            # 拼接歌名和歌手名作为文件名
            song_name = music_info.get("songname", "unknown")
            artist_name = music_info.get("artist", "unknown")
            file_name = f"{song_name} - {artist_name}"

            # 移除非法字符
            file_name = re.sub(r'[\/:*?"<>|]', "", file_name)
            music_path = os.path.join(music_data_dir, file_name)
            mp3_path = os.path.join(music_data_dir, f"{file_name}.mp3")

            print(f"正在下载 {file_name}...")
            # 异步下载音乐文件
            async with session.get(music_info["src"]) as response:
                if response.status == 200:
                    with open(music_path, "wb") as f:
                        while True:
                            chunk = await response.content.read(1024)
                            if not chunk:
                                break
                            f.write(chunk)
                    print(f"{file_name} 下载成功，保存到 {music_path}")

                    # 并发执行音频转换任务
                    asyncio.create_task(convert_to_mp3(file_name, music_path, mp3_path))
                else:
                    print(f"下载 {file_name} 失败，状态码：{response.status}")
        else:
            print(f"无法获取下载链接。")


# 主函数，处理所有歌曲下载
async def main():
    init()  # 初始化目录
    music_list = get_music_list(music_list_file)  # 从 list.json 文件中读取歌曲列表

    # 限制并发下载任务数量为 3
    semaphore = asyncio.Semaphore(3)

    async with aiohttp.ClientSession() as session:
        tasks = []
        for music in music_list:
            song_name = music.get("songname")
            songmid = music.get("songmid")

            if song_name and songmid:
                tasks.append(download_music(session, song_name, songmid, semaphore))

        # 并发执行所有下载任务
        await asyncio.gather(*tasks)


if __name__ == "__main__":
    asyncio.run(main())
