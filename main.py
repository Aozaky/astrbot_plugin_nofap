from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.star import Context, Star, register
import os
import json
from datetime import date, timedelta



def read_html_template(filepath="rank.html"):
    """读取HTML模板文件内容并返回字符串"""
    base_path = os.path.dirname(__file__)
    absolute_path = os.path.join(base_path, filepath)
    with open(absolute_path, "r", encoding="utf-8") as file:
        return file.read()


# 读取HTML模板
TMPL = read_html_template()


DATA_FILE = "data/astrbot-nofap.json"

@register(
    name = "astrbot-nofap",
    author = "aoz",
    desc = "一个简单的群内戒色榜插件",
    version = "v1.0.0"
)


class NoFap(Star):
    def __init__(self, context: Context):
        super().__init__(context)
        self.nofap_data = self.load_data()

    def load_data(self):
        """加载戒色数据，如果文件不存在则创建并返回空数据"""
        if not os.path.exists(DATA_FILE):
            return {}
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)


    def save_data(self):
        """保存戒色数据到文件"""
        with open(DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(self.nofap_data, f, ensure_ascii=False, indent=4)


    def get_user_data(self, group_id, user_id):
        """获取用户戒色数据，外层群，里层人"""
        if group_id not in self.nofap_data:
            self.nofap_data[group_id] = {}
        
        if user_id not in self.nofap_data[group_id]:
            self.nofap_data[group_id][user_id] = {
                "start_date": None,
                "days": 0,
                "user_name": None
            }
        return self.nofap_data[group_id][user_id]



    # nofap指令组
    @filter.command_group("nofap")
    def nofap(self):
        pass


    @nofap.command("mark", alias = ["check"])
    async def mark(self, event: AstrMessageEvent):
        """戒色打卡"""
        group_id = event.get_group_id()
        user_id = event.get_sender_id()
        user_data = self.get_user_data(group_id, user_id)
        today = date.today()
        today_str = today.strftime("%Y-%m-%d")



        user_data['user_name'] = event.get_sender_name() # 添加id对应的name


        last_mark_date = user_data.get('last_mark_date') # 判断是否重复打卡
        if last_mark_date == today_str:
            yield event.plain_result("喂喂！你今天已经打过卡了！别想骗过本小姐！")
            return

        user_data['days'] += 1
        user_data['start_date'] = user_data['start_date'] or today_str
        user_data['last_mark_date'] = today_str
        self.save_data()

        start_date_display = user_data['start_date']
        yield event.plain_result(f"戒色打卡成功！您已连续戒色 {user_data['days']} 天，戒色开始于 {start_date_display}，真是让本小姐刮目相看了呢！嗯嗯！")



    @nofap.command("update", alias = ["to"])
    async def update(self, event: AstrMessageEvent, days:int):
        '''修改戒色天数'''
        if days < 0:
            yield event.plain_result(f"为什么要输入负数啊喂！")
            return
        elif days == 0:
            yield event.plain_result(f"戒色失败了就老老实实 nofap fail 啊！")
            return
        
        group_id = event.get_group_id()
        user_id = event.get_sender_id()
        user_data = self.get_user_data(group_id, user_id)
        today = date.today()
        start_date = today - timedelta(days - 1)
        today_str = today.strftime("%Y-%m-%d")
        start_date_str = start_date.strftime("%Y-%m-%d")
        
        user_data['user_name'] = event.get_sender_name() # 添加id对应的name
        
        user_data['days'] = days
        user_data['start_date'] = start_date_str
        user_data['last_mark_date'] = today_str
        self.save_data()
        
        yield event.plain_result(f"戒色天数修改成功！您已连续戒色 {user_data['days']} 天，哇浪，这么厉害啊！")
    
    
    
    @nofap.command("rank")
    async def rank(self, event: AstrMessageEvent):
        """查看戒色榜"""

        group_id = event.get_group_id()
        
        if group_id not in self.nofap_data or not self.nofap_data[group_id]:
            yield event.plain_result("本小姐定睛一看，当前戒色榜空空如也！还没有人开始戒色呢！")
            return
            
        # 根据戒色天数排序用户
        ranked_users_data = sorted(self.nofap_data[group_id].items(), key=lambda item: item[1]['days'], reverse=True)
        items = []


        # 创建符合模板预期的数据格式 - 元组列表 [(排名, 用户数据), ...]
        for rank, (user_id, data) in enumerate(ranked_users_data, start=1):
            user_info = {
                'user_name': data['user_name'] or user_id,
                'days': data['days'],
                'start_date': data['start_date'] or "未开始"
            }
            items.append((rank, user_info))
            if rank >= 20:
                break
        
        # 传递正确的参数给模板
        url = await self.html_render(TMPL, {"items": items, "ranked_users_data": ranked_users_data})
        
        yield event.image_result(url)



    @nofap.command("fail", alias=["day0"])
    async def fail(self, event: AstrMessageEvent):
        """戒色失败，重置天数"""
        group_id = event.get_group_id()
        user_id = event.get_sender_id()
        user_data = self.get_user_data(group_id, user_id)

        if user_data['days'] == 0: #  如果已经是 0 天，提示用户
            yield event.plain_result("还没开始就想着失败？！")
            return

        user_data['days'] = 0
        user_data['start_date'] = None
        user_data['last_mark_date'] = None
        self.save_data()

        yield event.plain_result("诶诶！戒色失败了吗！！好吧，已经把你的数据归零了~")



    async def terminate(self):
        self.save_data()



