import os
import shutil

class ShadowManager:
    """
    管理项目文件/目录与其影子等效项之间的映射。
    影子文件/目录存储在<source_dir>/.auto-coder/shadows/中，
    并镜像原始项目的结构。
    
    如果提供了event_file_id，则影子文件存储在<source_dir>/.auto-coder/shadows/<event_file_id>/中。
    """
    
    def __init__(self, source_dir, event_file_id=None, ignore_clean_shadows=False):
        """
        使用项目根目录初始化。
        
        参数:
            source_dir (str): 项目根目录的绝对路径。
            event_file_id (str, optional): 事件文件ID，用于创建特定的影子目录。
            ignore_clean_shadows (bool, optional): 是否忽略清理影子目录。
        """
        self.source_dir = os.path.abspath(source_dir)
        self.ignore_clean_shadows = ignore_clean_shadows
        self.event_file_id = None        
        # # 根据是否提供了event_file_id来确定shadows_dir的路径
        # if event_file_id:       
        #     print("======" + event_file_id)
        # import traceback
        # traceback.print_stack()
        
        if event_file_id:
            event_file_id = self.get_event_file_id_from_path(event_file_id)
            self.event_file_id = event_file_id
            self.shadows_dir = os.path.join(self.source_dir, '.auto-coder', 'shadows', event_file_id)
        else:
            self.shadows_dir = os.path.join(self.source_dir, '.auto-coder', 'shadows')

        # 确保影子目录存在
        os.makedirs(self.shadows_dir, exist_ok=True)
        
        # 确保链接项目目录存在
        link_projects_dir = os.path.join(self.source_dir, '.auto-coder', 'shadows', 'link_projects')
        source_basename = os.path.basename(self.source_dir)
        os.makedirs(link_projects_dir, exist_ok=True)
        if self.event_file_id:
            self.link_projects_dir = os.path.join(link_projects_dir, self.event_file_id, source_basename)
        else:
            self.link_projects_dir = os.path.join(link_projects_dir, source_basename) 

        os.makedirs(self.link_projects_dir, exist_ok=True)                
        

    def get_event_file_id_from_path(self, path):
        """
        从给定路径中提取事件文件ID。
        
        参数:
            path (str): 项目路径
        
        返回:
            str: 事件文件ID
        """        
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
        if self.ignore_clean_shadows:
            return True

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

    def create_link_project(self):
        """
        创建链接项目，该项目是源目录的一个特殊副本，
        其中优先使用影子目录中的文件，如果影子目录中不存在则使用源目录中的文件。
        
        返回:
            str: 链接项目的路径
        """      
        # 清理链接项目目录
        self._clean_link_project_dir()
        # 创建链接项目
        self._create_links(self.source_dir, self.link_projects_dir)        
        return self.link_projects_dir
    
    def _clean_link_project_dir(self):
        """
        清理链接项目目录中的所有内容，但保留目录本身。
        
        返回:
            bool: 操作成功则为True，否则为False
        """
        if not os.path.exists(self.link_projects_dir):
            return True
            
        try:
            # 删除链接项目目录中的所有内容
            for item in os.listdir(self.link_projects_dir):
                item_path = os.path.join(self.link_projects_dir, item)
                if os.path.isfile(item_path) or os.path.islink(item_path):
                    os.unlink(item_path)
                elif os.path.isdir(item_path):
                    shutil.rmtree(item_path)
            
            return True
        except Exception as e:
            print(f"清理链接项目目录时出错: {str(e)}")
            return False

    def _create_links(self, source_path, link_path, rel_path=''):
        """
        递归创建从源目录到链接项目目录的链接
        
        参数:
            source_path: 当前处理的源目录路径
            link_path: 对应的链接项目目录路径
            rel_path: 相对于根源目录的相对路径
        """        
        # 获取源目录中的所有项目
        for item in os.listdir(source_path):
            # 跳过.auto-coder目录
            if item in ['.auto-coder', '.git']:
                continue
                
            source_item_path = os.path.join(source_path, item)
            link_item_path = os.path.join(link_path, item)
            current_rel_path = os.path.join(rel_path, item) if rel_path else item
            
            # 我们相当于遍历了所有目录，遇到 shadow_dir 和 source_dir 同时存在：
            # 则创建目录，遍历里面的文件，如果文件出现在shadow_dir里，则软链到shadow_dir，否则软链到source_dir里。
            # 如果目录不同时存在，则直接创建到 source_dir的软链。这样就能确保 link_project 和 source_dir 的结构完全一致。
            if os.path.isdir(source_item_path):
                # 构建在shadows_dir中可能存在的对应路径
                shadow_dir_path = os.path.join(self.shadows_dir, current_rel_path)
                
                # 2.1 如果目录在shadows_dir中存在
                if os.path.exists(shadow_dir_path) and os.path.isdir(shadow_dir_path):
                    # 创建对应的目录结构
                    os.makedirs(link_item_path, exist_ok=True)
                    
                    # 遍历源目录中的文件
                    for file_item in os.listdir(source_item_path):
                        source_file_path = os.path.join(source_item_path, file_item)
                        link_file_path = os.path.join(link_item_path, file_item)
                        shadow_file_path = os.path.join(shadow_dir_path, file_item)
                        
                        # 只处理文件，不处理子目录
                        if os.path.isfile(source_file_path):
                            # 检查链接文件是否已存在，如果存在则删除
                            if os.path.exists(link_file_path):
                                os.remove(link_file_path)
                                
                            # 如果文件在shadows_dir中存在，链接到shadows_dir中的文件
                            if os.path.exists(shadow_file_path) and os.path.isfile(shadow_file_path):
                                os.symlink(shadow_file_path, link_file_path)
                            # 否则链接到源目录中的文件
                            else:
                                os.symlink(source_file_path, link_file_path)
                    
                    # 递归处理子目录
                    self._create_links(source_item_path, link_item_path, current_rel_path)
                
                # 2.2 如果目录在shadows_dir中不存在，直接创建软链接
                else:
                    # 检查链接是否已存在，如果存在则删除
                    if os.path.exists(link_item_path):
                        if os.path.islink(link_item_path):
                            os.unlink(link_item_path)
                        elif os.path.isdir(link_item_path):
                            shutil.rmtree(link_item_path)
                        else:
                            os.remove(link_item_path)
                            
                    os.symlink(source_item_path, link_item_path)
            
            # 处理第一层级文件
            elif os.path.isfile(source_item_path):
                # 构建在shadows_dir中可能存在的对应文件路径
                shadow_file_path = os.path.join(self.shadows_dir, current_rel_path)
                
                # 检查链接文件是否已存在，如果存在则删除
                if os.path.exists(link_item_path):
                    os.remove(link_item_path)
                    
                # 如果文件在shadows_dir中存在，链接到shadows_dir中的文件
                if os.path.exists(shadow_file_path) and os.path.isfile(shadow_file_path):
                    os.symlink(shadow_file_path, link_item_path)
                # 否则链接到源目录中的文件
                else:
                    os.symlink(source_item_path, link_item_path)
                    
    def compare_directories(self):
        """
        比较源目录和链接项目目录之间的差异，并打印出来。
        
        返回:
            tuple: (源目录独有的文件/目录列表, 链接项目独有的文件/目录列表, 同时存在但类型不同的项目列表)
        """
        # 确保链接项目目录存在
        if not os.path.exists(self.link_projects_dir):
            print(f"链接项目目录不存在: {self.link_projects_dir}")
            return [], [], []
            
        source_only = []  # 只在源目录存在的文件/目录
        link_only = []    # 只在链接项目存在的文件/目录
        type_diff = []    # 类型不同的文件/目录
        
        # 递归比较目录结构
        self._compare_dir_recursive(self.source_dir, self.link_projects_dir, "", source_only, link_only, type_diff)
        
        # 打印差异结果
        print("\n目录结构比较结果:")
        
        if not (source_only or link_only or type_diff):
            print("✅ 目录结构完全一致")
            return source_only, link_only, type_diff
            
        if source_only:
            print("\n🔍 仅在源目录中存在:")
            for item in source_only:
                print(f"  - {item}")
                
        if link_only:
            print("\n🔍 仅在链接项目中存在:")
            for item in link_only:
                print(f"  - {item}")
                
        if type_diff:
            print("\n🔍 同名但类型不同的项目:")
            for item in type_diff:
                print(f"  - {item}")
                
        return source_only, link_only, type_diff
    
    def _compare_dir_recursive(self, source_path, link_path, rel_path, source_only, link_only, type_diff):
        """
        递归比较两个目录的差异
        
        参数:
            source_path: 源目录路径
            link_path: 链接项目目录路径
            rel_path: 当前处理的相对路径
            source_only: 仅在源目录存在的项目列表
            link_only: 仅在链接项目存在的项目列表
            type_diff: 同名但类型不同的项目列表
        """
        # 获取源目录和链接项目目录中的所有项目
        try:
            source_items = set(os.listdir(source_path))
        except (FileNotFoundError, PermissionError):
            source_items = set()
            
        try:
            link_items = set(os.listdir(link_path))
        except (FileNotFoundError, PermissionError):
            link_items = set()
            
        # 忽略特定目录
        ignored_dirs = ['.auto-coder', '.git']
        source_items = {item for item in source_items if item not in ignored_dirs}
        link_items = {item for item in link_items if item not in ignored_dirs}
        
        # 找出仅在源目录中存在的项目
        for item in source_items - link_items:
            item_rel_path = os.path.join(rel_path, item) if rel_path else item
            source_only.append(item_rel_path)
            
        # 找出仅在链接项目中存在的项目
        for item in link_items - source_items:
            item_rel_path = os.path.join(rel_path, item) if rel_path else item
            link_only.append(item_rel_path)
            
        # 比较同时存在的项目
        for item in source_items.intersection(link_items):
            # 跳过忽略的目录
            if item in ignored_dirs:
                continue
                
            source_item_path = os.path.join(source_path, item)
            link_item_path = os.path.join(link_path, item)
            item_rel_path = os.path.join(rel_path, item) if rel_path else item
            
            # 如果类型不同（一个是文件，一个是目录）
            source_is_dir = os.path.isdir(source_item_path)
            link_is_dir = os.path.isdir(link_item_path)
            
            if source_is_dir != link_is_dir:
                type_description = f"{item_rel_path} (源: {'目录' if source_is_dir else '文件'}, 链接: {'目录' if link_is_dir else '文件'})"
                type_diff.append(type_description)
            elif source_is_dir and link_is_dir:
                # 如果都是目录，递归比较
                self._compare_dir_recursive(
                    source_item_path, 
                    link_item_path, 
                    item_rel_path,
                    source_only, 
                    link_only, 
                    type_diff
                ) 