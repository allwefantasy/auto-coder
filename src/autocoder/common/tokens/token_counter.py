
"""
Token统计核心模块

提供基于VariableHolder.TOKENIZER_MODEL的文件和目录token统计功能
"""

import os
import re
import mimetypes
from pathlib import Path
from typing import List, Dict, Optional, Pattern, Union
from dataclasses import dataclass
from loguru import logger

from autocoder.rag.variable_holder import VariableHolder
from autocoder.common.files import read_file
from autocoder.common.ignorefiles.ignore_file_utils import should_ignore


@dataclass
class FileTokenStats:
    """单个文件的token统计信息"""
    file_path: str
    token_count: int
    error: Optional[str] = None
    skipped: bool = False
    skip_reason: Optional[str] = None

    @property
    def is_success(self) -> bool:
        """是否统计成功"""
        return self.error is None and not self.skipped

    def __str__(self) -> str:
        if self.skipped:
            return f"{self.file_path}: 跳过 ({self.skip_reason})"
        elif self.error:
            return f"{self.file_path}: 错误 ({self.error})"
        else:
            return f"{self.file_path}: {self.token_count} tokens"


@dataclass 
class DirectoryTokenStats:
    """目录token统计信息"""
    directory_path: str
    total_tokens: int
    file_stats: List[FileTokenStats]
    total_files: int
    successful_files: int
    skipped_files: int
    error_files: int

    @property
    def success_rate(self) -> float:
        """统计成功率"""
        if self.total_files == 0:
            return 0.0
        return self.successful_files / self.total_files

    def get_files_by_status(self, status: str) -> List[FileTokenStats]:
        """根据状态获取文件列表
        
        Args:
            status: 'success', 'skipped', 'error'
        """
        if status == 'success':
            return [f for f in self.file_stats if f.is_success]
        elif status == 'skipped':
            return [f for f in self.file_stats if f.skipped]
        elif status == 'error':
            return [f for f in self.file_stats if f.error is not None]
        else:
            return []

    def __str__(self) -> str:
        return (f"目录: {self.directory_path}\n"
                f"总计: {self.total_tokens} tokens\n"
                f"文件统计: {self.total_files}个文件 "
                f"({self.successful_files}成功, {self.skipped_files}跳过, {self.error_files}错误)")


class TokenStatsCalculator:
    """Token统计计算器"""
    
    # 默认的文本文件扩展名
    DEFAULT_TEXT_EXTENSIONS = {
        '.txt', '.md', '.py', '.js', '.ts', '.html', '.htm', '.css', '.scss', '.sass',
        '.json', '.xml', '.yaml', '.yml', '.toml', '.ini', '.cfg', '.conf', '.config',
        '.sh', '.bash', '.zsh', '.fish', '.ps1', '.bat', '.cmd', '.java', '.c', '.cpp',
        '.cc', '.cxx', '.h', '.hpp', '.hxx', '.cs', '.php', '.rb', '.go', '.rs', '.kt',
        '.swift', '.scala', '.clj', '.cljs', '.edn', '.sql', '.r', '.R', '.m', '.mm',
        '.pl', '.pm', '.t', '.lua', '.vim', '.tex', '.latex', '.rst', '.adoc', '.org',
        '.dockerfile', '.makefile', '.cmake', '.gradle', '.properties', '.log',
        '.csv', '.tsv', '.svg', '.dockerfile'
    }

    # 默认的二进制文件扩展名（明确跳过）
    DEFAULT_BINARY_EXTENSIONS = {
        '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.tif', '.webp', '.ico',
        '.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx', '.odt', '.ods', '.odp',
        '.zip', '.tar', '.gz', '.bz2', '.xz', '.rar', '.7z', '.jar', '.war', '.ear',
        '.exe', '.dll', '.so', '.dylib', '.a', '.lib', '.o', '.obj', '.pyc', '.pyo',
        '.class', '.dex', '.apk', '.ipa', '.dmg', '.iso', '.img', '.bin', '.dat',
        '.db', '.sqlite', '.sqlite3', '.mdb', '.accdb', '.frm', '.myd', '.myi',
        '.mp3', '.mp4', '.avi', '.mkv', '.mov', '.wmv', '.flv', '.wav', '.ogg', '.flac',
        '.ttf', '.otf', '.woff', '.woff2', '.eot', '.swf', '.fla'
    }

    def __init__(self, 
                 text_extensions: Optional[set] = None,
                 binary_extensions: Optional[set] = None,
                 use_ignore_files: bool = True,
                 project_root: Optional[str] = None):
        """
        初始化Token统计计算器
        
        Args:
            text_extensions: 文本文件扩展名集合，None使用默认
            binary_extensions: 二进制文件扩展名集合，None使用默认
            use_ignore_files: 是否使用.autocoderignore文件过滤
            project_root: 项目根目录，用于ignore文件判断
        """
        self.text_extensions = text_extensions or self.DEFAULT_TEXT_EXTENSIONS
        self.binary_extensions = binary_extensions or self.DEFAULT_BINARY_EXTENSIONS
        self.use_ignore_files = use_ignore_files
        self.project_root = project_root or os.getcwd()

    def _is_text_file(self, file_path: str) -> tuple[bool, str]:
        """
        判断文件是否为文本文件
        
        Returns:
            (is_text, reason) - 是否为文本文件和判断原因
        """
        file_path_lower = file_path.lower()
        file_ext = Path(file_path).suffix.lower()
        
        # 检查是否在明确的二进制文件列表中
        if file_ext in self.binary_extensions:
            return False, f"二进制文件扩展名: {file_ext}"
        
        # 检查是否在明确的文本文件列表中
        if file_ext in self.text_extensions:
            return True, f"文本文件扩展名: {file_ext}"
        
        # 使用mimetypes模块判断
        mime_type, _ = mimetypes.guess_type(file_path)
        if mime_type:
            if mime_type.startswith('text/'):
                return True, f"MIME类型: {mime_type}"
            elif mime_type.startswith(('image/', 'video/', 'audio/', 'application/octet-stream')):
                return False, f"MIME类型: {mime_type}"
        
        # 特殊文件名处理
        filename = os.path.basename(file_path_lower)
        if filename in {'makefile', 'dockerfile', 'readme', 'license', 'changelog', 'authors'}:
            return True, f"特殊文件名: {filename}"
        
        # 无扩展名文件，尝试读取少量内容判断
        if not file_ext:
            try:
                with open(file_path, 'rb') as f:
                    chunk = f.read(1024)  # 读取前1KB
                    # 检查是否包含null字节（二进制文件特征）
                    if b'\x00' in chunk:
                        return False, "包含null字节"
                    # 尝试解码为UTF-8
                    try:
                        chunk.decode('utf-8')
                        return True, "UTF-8可解码的无扩展名文件"
                    except UnicodeDecodeError:
                        return False, "UTF-8解码失败"
            except Exception as e:
                return False, f"读取文件错误: {str(e)}"
        
        # 默认按扩展名未知的文件当作文本文件处理
        return True, "未知扩展名，默认当作文本文件"

    def _count_file_tokens(self, file_path: str) -> int:
        """
        统计单个文件的token数量
        
        Args:
            file_path: 文件路径
            
        Returns:
            token数量，失败返回-1
        """
        try:
            if VariableHolder.TOKENIZER_MODEL is None:
                raise ValueError("TOKENIZER_MODEL未初始化")
            
            content = read_file(file_path)
            encoded = VariableHolder.TOKENIZER_MODEL.encode(content)
            return len(encoded.ids)
            
        except Exception as e:
            logger.error(f"统计文件token失败 {file_path}: {str(e)}")
            return -1

    def count_file_tokens(self, file_path: str) -> FileTokenStats:
        """
        统计单个文件的token数量
        
        Args:
            file_path: 文件路径
            
        Returns:
            FileTokenStats对象
        """
        file_path = os.path.abspath(file_path)
        
        # 检查文件是否存在
        if not os.path.exists(file_path):
            return FileTokenStats(
                file_path=file_path,
                token_count=0,
                error="文件不存在"
            )
        
        if not os.path.isfile(file_path):
            return FileTokenStats(
                file_path=file_path,
                token_count=0,
                error="不是文件"
            )
        
        # 检查是否应该忽略
        if self.use_ignore_files and should_ignore(file_path, self.project_root):
            return FileTokenStats(
                file_path=file_path,
                token_count=0,
                skipped=True,
                skip_reason="匹配ignore规则"
            )
        
        # 检查是否为文本文件
        is_text, reason = self._is_text_file(file_path)
        if not is_text:
            return FileTokenStats(
                file_path=file_path,
                token_count=0,
                skipped=True,
                skip_reason=f"非文本文件: {reason}"
            )
        
        # 统计token
        token_count = self._count_file_tokens(file_path)
        if token_count == -1:
            return FileTokenStats(
                file_path=file_path,
                token_count=0,
                error="token统计失败"
            )
        
        return FileTokenStats(
            file_path=file_path,
            token_count=token_count
        )

    def count_directory_tokens(self, 
                             directory_path: str,
                             file_pattern: Optional[Union[str, Pattern]] = None,
                             recursive: bool = True) -> DirectoryTokenStats:
        """
        统计目录中所有文件的token数量
        
        Args:
            directory_path: 目录路径
            file_pattern: 文件名正则表达式模式，None表示匹配所有文件
            recursive: 是否递归处理子目录
            
        Returns:
            DirectoryTokenStats对象
        """
        directory_path = os.path.abspath(directory_path)
        
        if not os.path.exists(directory_path):
            return DirectoryTokenStats(
                directory_path=directory_path,
                total_tokens=0,
                file_stats=[],
                total_files=0,
                successful_files=0,
                skipped_files=0,
                error_files=0
            )
        
        if not os.path.isdir(directory_path):
            return DirectoryTokenStats(
                directory_path=directory_path,
                total_tokens=0,
                file_stats=[],
                total_files=0,
                successful_files=0,
                skipped_files=0,
                error_files=0
            )
        
        # 编译正则表达式
        pattern = None
        if file_pattern:
            if isinstance(file_pattern, str):
                try:
                    pattern = re.compile(file_pattern)
                except re.error as e:
                    logger.error(f"正则表达式编译失败: {file_pattern}, 错误: {e}")
                    pattern = None
            else:
                pattern = file_pattern
        
        file_stats = []
        
        # 遍历目录
        if recursive:
            for root, dirs, files in os.walk(directory_path):
                # 过滤被ignore的目录
                if self.use_ignore_files:
                    dirs[:] = [d for d in dirs if not should_ignore(
                        os.path.join(root, d), self.project_root)]
                
                for file in files:
                    file_path = os.path.join(root, file)
                    
                    # 应用文件名正则过滤
                    if pattern and not pattern.search(file):
                        continue
                    
                    stats = self.count_file_tokens(file_path)
                    file_stats.append(stats)
        else:
            # 非递归模式，只处理当前目录
            try:
                for item in os.listdir(directory_path):
                    file_path = os.path.join(directory_path, item)
                    
                    if not os.path.isfile(file_path):
                        continue
                    
                    # 应用文件名正则过滤
                    if pattern and not pattern.search(item):
                        continue
                    
                    stats = self.count_file_tokens(file_path)
                    file_stats.append(stats)
            except PermissionError as e:
                logger.error(f"访问目录失败: {directory_path}, 错误: {e}")
        
        # 统计结果
        total_tokens = sum(f.token_count for f in file_stats if f.is_success)
        total_files = len(file_stats)
        successful_files = len([f for f in file_stats if f.is_success])
        skipped_files = len([f for f in file_stats if f.skipped])
        error_files = len([f for f in file_stats if f.error is not None])
        
        return DirectoryTokenStats(
            directory_path=directory_path,
            total_tokens=total_tokens,
            file_stats=file_stats,
            total_files=total_files,
            successful_files=successful_files,
            skipped_files=skipped_files,
            error_files=error_files
        )

    def get_summary_report(self, stats: DirectoryTokenStats) -> str:
        """
        生成目录统计的摘要报告
        
        Args:
            stats: 目录统计结果
            
        Returns:
            格式化的摘要报告字符串
        """
        report_lines = [
            f"=== Token统计报告 ===",
            f"目录: {stats.directory_path}",
            f"",
            f"总体统计:",
            f"  总tokens: {stats.total_tokens:,}",
            f"  总文件数: {stats.total_files}",
            f"  成功统计: {stats.successful_files} ({stats.success_rate:.1%})",
            f"  跳过文件: {stats.skipped_files}",
            f"  错误文件: {stats.error_files}",
            f""
        ]
        
        # 成功的文件统计（按token数量排序）
        success_files = sorted(
            stats.get_files_by_status('success'),
            key=lambda x: x.token_count,
            reverse=True
        )
        
        if success_files:
            report_lines.append("成功统计的文件 (按token数量排序):")
            for file_stat in success_files[:10]:  # 只显示前10个
                report_lines.append(f"  {file_stat.token_count:>8,} tokens - {file_stat.file_path}")
            
            if len(success_files) > 10:
                report_lines.append(f"  ... 还有 {len(success_files) - 10} 个文件")
            report_lines.append("")
        
        # 跳过的文件
        skipped_files = stats.get_files_by_status('skipped')
        if skipped_files:
            report_lines.append("跳过的文件:")
            for file_stat in skipped_files[:5]:  # 只显示前5个
                report_lines.append(f"  {file_stat.skip_reason} - {file_stat.file_path}")
            
            if len(skipped_files) > 5:
                report_lines.append(f"  ... 还有 {len(skipped_files) - 5} 个跳过的文件")
            report_lines.append("")
        
        # 错误的文件
        error_files = stats.get_files_by_status('error')
        if error_files:
            report_lines.append("错误的文件:")
            for file_stat in error_files[:5]:  # 只显示前5个
                report_lines.append(f"  {file_stat.error} - {file_stat.file_path}")
            
            if len(error_files) > 5:
                report_lines.append(f"  ... 还有 {len(error_files) - 5} 个错误的文件")
        
        return "\n".join(report_lines)

