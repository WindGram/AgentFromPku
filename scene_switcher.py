import os
import json
from PIL import Image, ImageTk
import logging

def load_config():
    """加载 config.json 文件"""
    try:
        with open("config.json", "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        print("错误：缺少 config.json 文件！请复制 config.example.json 并填写密钥")
        exit(1)

# 全局配置
config = load_config()
API_KEY_1 = config["api_keys"]["yannanyuan"] 
API_KEY_2 = config["api_keys"]["shaoyuan"]
API_KEY_3 = config["api_keys"]["weiminghu"]

logger = logging.getLogger(__name__)

garden_background_mapping = {
    "燕南园": "bk1.jpg",
    "勺园": "swtsdx.jpg",  # 示例：可根据实际情况添加更多园子和对应的图片
    # 可以继续添加其他园子及其对应的背景图片文件名
    "未名湖": "wmlake.jpg",
}

def switch_scene(original_content, ui_builder, api_client):
    """
    切换场景的函数，根据 AI 回复的内容切换背景图片
    :param original_content: AI 回复的原始内容
    :param ui_builder: UI构建器实例
    :param api_client: API客户端实例
    """
    # 调试输出原始内容
    logger.info(f"检测场景切换，原始内容: {original_content[:100]}...")
    
    for garden, image_file in garden_background_mapping.items():
        # 更灵活的匹配方式
        if f"[{garden}]" in original_content:
            try:
                logger.info(f"切换到场景: {garden}, 使用背景: {image_file}")
                
                # 使用ui_builder的方法设置背景
                ui_builder.set_background(image_file)
                
                # 根据场景切换API密钥和角色信息
                if garden == "燕南园":
                    new_api_key = API_KEY_1
                    api_client.change_api_key(new_api_key)
                    api_client.current_conversation_id = None
                    api_client.files = []
                    
                    # 更新角色信息
                    ui_builder.add_photo("zgq.jpg")
                    ui_builder.set_name("朱光潜")
                    ui_builder.set_intro("  朱光潜，字孟实，安徽桐城人。他早年留学欧洲，获英国爱丁堡大学文学硕士、法国斯特拉斯堡大学哲学博士学位，系统研究西方美学，融通中西学术传统。\n   朱光潜自1933年起受聘于北京大学西语系，后长期担任教授，并曾兼任文学院代理院长。1952年全国院系调整后，他转入北大哲学系，专注美学研究与教学，主持创办了中国首个美学教研室，培养了大批美学人才。他的代表作《文艺心理学》《谈美》《西方美学史》等深刻影响了中国现代美学发展，其中《西方美学史》是首部由中国学者撰写的系统研究西方美学的权威著作，奠定了北大在中国美学研究的核心地位。\n  朱光潜晚年仍坚持在燕南园住所授课，其治学严谨与人格魅力成为北大精神象征之一。他主张“人生的艺术化”，倡导美育与人文关怀，至今未名湖畔仍流传着他与学生谈学论道的佳话。")

                elif garden == "勺园":
                    new_api_key = API_KEY_2
                    api_client.change_api_key(new_api_key)
                    api_client.current_conversation_id = None
                    api_client.files = []
                    
                    # 更新角色信息
                    ui_builder.add_photo("swts.jpg")
                    ui_builder.set_name("塞万提斯之魂")
                    ui_builder.set_intro("    在北大勺园的绿荫深处，静立着一座塞万提斯的青铜雕像——这位西班牙文学巨匠手持书卷，目光深邃，仿佛穿越时空注视着来往的学子。他是《堂吉诃德》的作者，文艺复兴时期的文学传奇，用笔尖编织了理想与现实的永恒对话。\n    如今，他的灵魂仍徘徊于此。当微风拂过雕像，或是你驻足凝望时，或许能听见他低语：关于骑士的幻想、关于文学的狂热、关于人性与命运的沉思。他愿与好奇的访客交谈，分享塞维利亚的阳光、阿尔及尔的囚牢、马德里的辉煌，以及一个作家眼中永不褪色的世界。\n  （走近雕像，试着向他提问——这位四百年前的文豪，会给你意想不到的回答。）\n    （注：北大勺园的塞万提斯雕像是中西文化交流的象征，由中国西班牙友好协会于1986年捐赠。）")
                elif garden == "未名湖":
                    new_api_key = API_KEY_3
                    api_client.change_api_key(new_api_key)
                    api_client.current_conversation_id = None
                    api_client.files = []
                    
                    # 更新角色信息
                    ui_builder.add_photo("thisisphoto.png")
                    ui_builder.set_name("nyw")
                    ui_builder.set_intro("北京大学信息科学技术学院，准大二学生nyw，你可以和他聊很多东西")

                return
            
            except Exception as e:
                logger.error(f"切换场景({garden})失败: {e}")
    
    logger.info("未找到匹配的地点，不进行背景切换")