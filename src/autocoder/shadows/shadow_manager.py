import os
import shutil

class ShadowManager:
    """
    管理项目文件/目录与其影子等效项之间的映射。
    影子文件/目录存储在<source_dir>/.auto-coder/shadows/中，
    并镜像原始项目的结构。
    
    如果提供了event_file_id，则影子文件存储在<source_dir>/.auto-coder/shadows/<event_file_id>/中。
    """
    
    def __init__(self, source_dir, event_file_id=None):
        """
        使用项目根目录初始化。
        
        参数:
            source_dir (str): 项目根目录的绝对路径。
            event_file_id (str, optional): 事件文件ID，用于创建特定的影子目录。
        """
        self.source_dir = os.path.abspath(source_dir)
        
        # # 根据是否提供了event_file_id来确定shadows_dir的路径
        # if event_file_id:       
        #     print("======" + event_file_id)
        # import traceback
        # traceback.print_stack()
        
        if event_file_id:
            event_file_id = self.get_event_file_id_from_path(event_file_id)
            self.shadows_dir = os.path.join(self.source_dir, '.auto-coder', 'shadows', event_file_id)
        else:
            self.shadows_dir = os.path.join(self.source_dir, '.auto-coder', 'shadows')
        
        # 确保影子目录存在
        os.makedirs(self.shadows_dir, exist_ok=True)

    def get_event_file_id_from_path(self, path):
        """
        从给定路径中提取事件文件ID。
        
        参数:
            path (str): 项目路径
        
        返回:
            str: 事件文件ID
        """
        if not path.endswith('.jsonl'):
            return event_file_id
        temp = os.path.basename(path)
        ##  获取不带后缀的event_file_id
        event_file_id = os.path.splitext(temp)[0]
        return event_file_id
    
    def to_shadow_path(self, path):
        """
        将项目路径转换为其影子等效路径。
        
        参数:
            path (str): 源目录内的路径（绝对或相对）
            
        返回:
            str: 对应影子位置的绝对路径
            
        异常:
            ValueError: 如果路径不在源目录内
        """
        # 确保我们有一个绝对路径
        abs_path = os.path.abspath(path)
        
        # 检查路径是否在源目录内
        if not abs_path.startswith(self.source_dir):
            raise ValueError(f"路径 {path} 不在源目录 {self.source_dir} 内")
        
        # 获取相对于source_dir的相对路径
        rel_path = os.path.relpath(abs_path, self.source_dir)
        
        # 创建影子路径
        shadow_path = os.path.join(self.shadows_dir, rel_path)
        
        return shadow_path
    
    def from_shadow_path(self, shadow_path):
        """
        将影子路径转换回其项目等效路径。
        
        参数:
            shadow_path (str): 影子目录内的路径（绝对或相对）
            
        返回:
            str: 对应项目位置的绝对路径
            
        异常:
            ValueError: 如果路径不在影子目录内
        """
        # 确保我们有一个绝对路径
        abs_shadow_path = os.path.abspath(shadow_path)
        
        # 检查路径是否在影子目录内
        if not abs_shadow_path.startswith(self.shadows_dir):
            raise ValueError(f"路径 {shadow_path} 不在影子目录 {self.shadows_dir} 内")
        
        # 获取相对于shadows_dir的相对路径
        rel_path = os.path.relpath(abs_shadow_path, self.shadows_dir)
        
        # 创建项目路径
        project_path = os.path.join(self.source_dir, rel_path)
        
        return project_path
    
    def ensure_shadow_dir_exists(self, path):
        """
        确保给定路径的影子目录存在。
        
        参数:
            path (str): 需要创建影子目录的项目路径
            
        返回:
            str: 影子路径
        """
        shadow_path = self.to_shadow_path(path)
        
        if os.path.isdir(path):
            os.makedirs(shadow_path, exist_ok=True)
        else:
            os.makedirs(os.path.dirname(shadow_path), exist_ok=True)
            
        return shadow_path
    
    def is_shadow_path(self, path):
        """
        检查路径是否为影子路径。
        
        参数:
            path (str): 要检查的路径
            
        返回:
            bool: 如果路径在影子目录内，则为True
        """
        abs_path = os.path.abspath(path)
        return abs_path.startswith(self.shadows_dir)
    
    def save_file(self, file_path, content):
        """
        将内容保存到对应给定项目文件路径的影子文件中。
        
        参数:
            file_path (str): 项目文件路径
            content (str): 要保存的内容
            
        返回:
            str: 保存内容的影子路径
        """
        shadow_path = self.to_shadow_path(file_path)
        
        # 确保父目录存在
        os.makedirs(os.path.dirname(shadow_path), exist_ok=True)
        
        # 将内容写入影子文件
        with open(shadow_path, 'w', encoding='utf-8') as f:
            f.write(content)
            
        return shadow_path
    
    def update_file(self, file_path, content):
        """
        更新对应给定项目文件路径的影子文件。
        如果影子文件不存在，将创建它。
        
        参数:
            file_path (str): 项目文件路径
            content (str): 要更新的内容
            
        返回:
            str: 更新内容的影子路径
        """
        # 此实现本质上与save_file相同
        return self.save_file(file_path, content)
    
    def read_file(self, file_path):
        """
        从对应给定项目文件路径的影子文件中读取内容。
        
        参数:
            file_path (str): 项目文件路径
            
        返回:
            str: 影子文件的内容
            
        异常:
            FileNotFoundError: 如果影子文件不存在
        """
        shadow_path = self.to_shadow_path(file_path)
        
        with open(shadow_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        return content
    
    def delete_file(self, file_path):
        """
        删除对应给定项目文件路径的影子文件。
        
        参数:
            file_path (str): 项目文件路径
            
        返回:
            bool: 如果文件被删除则为True，如果不存在则为False
        """
        shadow_path = self.to_shadow_path(file_path)
        
        if os.path.exists(shadow_path):
            os.remove(shadow_path)
            return True
        
        return False 
        
    def clean_shadows(self):
        """
        清理影子目录中的所有文件和子目录，但保留影子目录本身。
        
        返回:
            bool: 操作成功则为True，否则为False
        """
        if not os.path.exists(self.shadows_dir):
            return True
            
        try:
            # 删除影子目录中的所有内容
            for item in os.listdir(self.shadows_dir):
                item_path = os.path.join(self.shadows_dir, item)
                if os.path.isfile(item_path):
                    os.unlink(item_path)
                elif os.path.isdir(item_path):
                    shutil.rmtree(item_path)
            
            return True
        except Exception as e:
            print(f"清理影子目录时出错: {str(e)}")
            return False 