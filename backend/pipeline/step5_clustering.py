"""
Step 5: 主题聚类 - 将相似内容聚类成合集
"""
import json
import logging
import re
from typing import List, Dict, Any, Optional
from pathlib import Path

# 导入依赖
from ..utils.llm_client import LLMClient
from ..core.shared_config import PROMPT_FILES, METADATA_DIR, MAX_CLIPS_PER_COLLECTION

logger = logging.getLogger(__name__)

class ClusteringEngine:
    """主题聚类引擎"""
    
    def __init__(self, metadata_dir: Optional[Path] = None, prompt_files: Dict = None):
        self.llm_client = LLMClient()
        
        # 加载提示词
        prompt_files_to_use = prompt_files if prompt_files is not None else PROMPT_FILES
        with open(prompt_files_to_use['clustering'], 'r', encoding='utf-8') as f:
            self.clustering_prompt = f.read()
        
        # 使用传入的metadata_dir或默认值
        if metadata_dir is None:
            metadata_dir = METADATA_DIR
        self.metadata_dir = metadata_dir
    
    def cluster_clips(self, clips_with_titles: List[Dict]) -> List[Dict]:
        """
        对片段进行主题聚类
        
        Args:
            clips_with_titles: 带标题的片段列表
            
        Returns:
            合集数据列表
        """
        logger.info("开始进行主题聚类...")
        
        # 准备聚类数据
        clips_for_clustering = []
        for clip in clips_with_titles:
            clips_for_clustering.append({
                'id': clip['id'],
                'title': clip.get('generated_title', clip['outline']),
                'summary': clip.get('recommend_reason', ''),
                'score': clip.get('final_score', 0)
            })
        
        # 首先进行基于关键词的预聚类
        pre_clusters = self._pre_cluster_by_keywords(clips_for_clustering)
        
        # 构建完整的提示词
        full_prompt = self.clustering_prompt + "\n\n以下是视频切片列表：\n"
        for i, clip in enumerate(clips_for_clustering, 1):
            full_prompt += f"{i}. 标题：{clip['title']}\n   摘要：{clip['summary']}\n   评分：{clip['score']:.2f}\n\n"
        
        # 添加预聚类结果作为参考
        if pre_clusters:
            full_prompt += "\n\n基于关键词的预聚类结果（仅供参考）：\n"
            for theme, clip_ids in pre_clusters.items():
                full_prompt += f"{theme}: {', '.join(clip_ids)}\n"
        
        try:
            # 调用大模型进行聚类
            response = self.llm_client.call_with_retry(full_prompt)
            
            # 解析JSON响应
            collections_data = self.llm_client.parse_json_response(response)
            
            # 验证和清理合集数据
            validated_collections = self._validate_collections(collections_data, clips_with_titles)
            
            # Si no hubo colecciones utiles desde LLM, usar fallback robusto:
            # 1) pre-cluster por keywords, 2) colecciones por score.
            if len(validated_collections) < 1:
                if pre_clusters:
                    logger.warning("LLM no devolvio colecciones validas; usando pre-cluster por keywords.")
                    validated_collections = self._create_collections_from_pre_clusters(pre_clusters, clips_with_titles)
                else:
                    logger.warning("LLM y pre-cluster sin resultado; usando fallback por score.")
                    validated_collections = self._create_default_collections(clips_with_titles)
            
            logger.info(f"主题聚类完成，共{len(validated_collections)}个合集")
            return validated_collections
            
        except Exception as e:
            logger.error(f"主题聚类失败: {str(e)}")
            # 使用预聚类结果作为备选
            if pre_clusters:
                logger.info("使用预聚类结果作为备选方案")
                return self._create_collections_from_pre_clusters(pre_clusters, clips_with_titles)
            # 返回默认聚类结果
            return self._create_default_collections(clips_with_titles)
    
    def _pre_cluster_by_keywords(self, clips: List[Dict]) -> Dict[str, List[str]]:
        """
        基于关键词进行预聚类
        
        Args:
            clips: 片段列表
            
        Returns:
            预聚类结果
        """
        # 定义主题关键词
        theme_keywords = {
            'Finanzas e inversion': [
                'inversion', 'finanzas', 'bolsa', 'acciones', 'fondos', 'dinero', 'rentabilidad',
                'mercado', 'trading', 'ahorro'
            ],
            'Carrera y habilidades': [
                'trabajo', 'carrera', 'habilidad', 'aprendizaje', 'productividad',
                'empleo', 'profesional', 'crecimiento'
            ],
            'Analisis social': [
                'sociedad', 'plataforma', 'comunidad', 'internet', 'tendencia',
                'industria', 'fenomeno', 'analisis'
            ],
            'Cultura y estilos de vida': [
                'cultura', 'idioma', 'costumbre', 'pais', 'comida', 'viaje', 'tradicion'
            ],
            'Streaming e interaccion': [
                'stream', 'directo', 'chat', 'audiencia', 'interaccion', 'fans', 'reaccion'
            ],
            'Relaciones y emociones': [
                'relacion', 'emocion', 'psicologia', 'social', 'pareja', 'comunicacion'
            ],
            'Salud y bienestar': [
                'salud', 'bienestar', 'rutina', 'ejercicio', 'alimentacion', 'habito'
            ],
            'Creacion de contenido': [
                'contenido', 'creador', 'edicion', 'guion', 'canal', 'youtube', 'tiktok', 'estrategia'
            ]
        }
        
        pre_clusters = {theme: [] for theme in theme_keywords.keys()}
        
        for clip in clips:
            # 合并标题和摘要进行关键词匹配
            text = f"{clip['title']} {clip['summary']}".lower()
            
            # 计算每个主题的匹配分数
            theme_scores = {}
            for theme, keywords in theme_keywords.items():
                score = sum(1 for keyword in keywords if keyword in text)
                if score > 0:
                    theme_scores[theme] = score
            
            # 选择匹配分数最高的主题
            if theme_scores:
                best_theme = max(theme_scores.keys(), key=lambda k: theme_scores[k])
                pre_clusters[best_theme].append(clip['id'])
        
        # 过滤掉空的主题
        return {theme: clip_ids for theme, clip_ids in pre_clusters.items() if len(clip_ids) >= 2}
    
    def _create_collections_from_pre_clusters(self, pre_clusters: Dict[str, List[str]], clips_with_titles: List[Dict]) -> List[Dict]:
        """
        从预聚类结果创建合集
        
        Args:
            pre_clusters: 预聚类结果
            clips_with_titles: 片段数据
            
        Returns:
            合集数据列表
        """
        collections = []
        collection_id = 1
        
        # 主题标题映射
        theme_titles = {
            'Finanzas e inversion': 'Ideas clave de finanzas e inversion',
            'Carrera y habilidades': 'Crecimiento profesional y habilidades',
            'Analisis social': 'Lectura social y tendencias',
            'Cultura y estilos de vida': 'Cultura y estilos de vida',
            'Streaming e interaccion': 'Momentos de streaming e interaccion',
            'Relaciones y emociones': 'Relaciones y emociones',
            'Salud y bienestar': 'Salud y bienestar',
            'Creacion de contenido': 'Creacion de contenido y plataforma'
        }
        
        # 主题简介映射
        theme_summaries = {
            'Finanzas e inversion': 'Fragmentos sobre dinero, decisiones de inversion y lectura de mercado.',
            'Carrera y habilidades': 'Momentos centrados en crecimiento laboral, habilidades y aprendizaje.',
            'Analisis social': 'Observaciones sobre comportamiento social, comunidad y plataformas.',
            'Cultura y estilos de vida': 'Clips con enfoque cultural, costumbres y estilo de vida.',
            'Streaming e interaccion': 'Interacciones destacadas con audiencia y dinamicas de directo.',
            'Relaciones y emociones': 'Conversaciones sobre relaciones, emociones y psicologia social.',
            'Salud y bienestar': 'Recomendaciones practicas sobre bienestar, habitos y rutina.',
            'Creacion de contenido': 'Ideas para creadores, narrativa y distribucion en plataformas.'
        }
        
        for theme, clip_ids in pre_clusters.items():
            # 限制每个合集的片段数量
            if len(clip_ids) > MAX_CLIPS_PER_COLLECTION:
                clip_ids = clip_ids[:MAX_CLIPS_PER_COLLECTION]
            
            collections.append({
                'id': str(collection_id),
                'collection_title': theme_titles.get(theme, theme),
                'collection_summary': theme_summaries.get(theme, f'Coleccion de fragmentos destacados sobre {theme}.'),
                'clip_ids': clip_ids
            })
            collection_id += 1
        
        return collections
    
    def _validate_collections(self, collections_data: List[Dict], clips_with_titles: List[Dict]) -> List[Dict]:
        """
        验证和清理合集数据
        
        Args:
            collections_data: 原始合集数据
            clips_with_titles: 片段数据
            
        Returns:
            验证后的合集数据
        """
        validated_collections = []
        
        for i, collection in enumerate(collections_data):
            try:
                # 验证必需字段
                if not all(key in collection for key in ['collection_title', 'collection_summary', 'clips']):
                    logger.warning(f"合集 {i} 缺少必需字段，跳过")
                    continue
                
                # 验证片段列表
                clip_titles = collection['clips']
                valid_clip_ids = []
                
                for clip_title in clip_titles:
                    # 根据标题找到对应的片段ID
                    for clip in clips_with_titles:
                        if (clip.get('generated_title', clip['outline']) == clip_title or 
                            clip['outline'] == clip_title):
                            valid_clip_ids.append(clip['id'])
                            break
                
                if len(valid_clip_ids) < 2:
                    logger.warning(f"合集 {i} 有效片段少于2个，跳过")
                    continue
                
                # 限制每个合集的片段数量
                if len(valid_clip_ids) > MAX_CLIPS_PER_COLLECTION:
                    valid_clip_ids = valid_clip_ids[:MAX_CLIPS_PER_COLLECTION]
                
                validated_collection = {
                    'id': str(i + 1),
                    'collection_title': collection['collection_title'],
                    'collection_summary': collection['collection_summary'],
                    'clip_ids': valid_clip_ids
                }
                
                validated_collections.append(validated_collection)
                
            except Exception as e:
                logger.error(f"验证合集 {i} 失败: {str(e)}")
                continue
        
        return validated_collections
    
    def _create_default_collections(self, clips_with_titles: List[Dict]) -> List[Dict]:
        """
        创建默认合集（当聚类失败时）
        
        Args:
            clips_with_titles: 片段数据
            
        Returns:
            默认合集数据
        """
        logger.info("创建默认合集...")
        
        # 按评分分组
        high_score = []
        medium_score = []
        
        for clip in clips_with_titles:
            score = clip.get('final_score', 0)
            if score >= 0.8:
                high_score.append(clip)
            elif score >= 0.6:
                medium_score.append(clip)
        
        collections = []
        
        # 创建高分合集
        if len(high_score) >= 2:
            collections.append({
                'id': '1',
                'collection_title': 'Selecciones de mayor puntaje',
                'collection_summary': 'Coleccion con los fragmentos mejor evaluados.',
                'clip_ids': [clip['id'] for clip in high_score[:MAX_CLIPS_PER_COLLECTION]]
            })
        
        # 创建中等分合集
        if len(medium_score) >= 2:
            collections.append({
                'id': '2',
                'collection_title': 'Recomendaciones de calidad',
                'collection_summary': 'Coleccion de contenido relevante y consistente.',
                'clip_ids': [clip['id'] for clip in medium_score[:MAX_CLIPS_PER_COLLECTION]]
            })
        
        return collections
    
    def save_collections(self, collections_data: List[Dict], output_path: Optional[Path] = None) -> Path:
        """
        保存合集数据
        
        Args:
            collections_data: 合集数据
            output_path: 输出路径
            
        Returns:
            保存的文件路径
        """
        if output_path is None:
            output_path = self.metadata_dir / "collections.json"
        
        # 确保目录存在
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # 保存数据
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(collections_data, f, ensure_ascii=False, indent=2)
        
        logger.info(f"合集数据已保存到: {output_path}")
        return output_path
    
    def load_collections(self, input_path: Path) -> List[Dict]:
        """
        从文件加载合集数据
        
        Args:
            input_path: 输入文件路径
            
        Returns:
            合集数据
        """
        with open(input_path, 'r', encoding='utf-8') as f:
            return json.load(f)

def run_step5_clustering(clips_with_titles_path: Path, output_path: Optional[Path] = None, metadata_dir: Optional[str] = None, prompt_files: Dict = None) -> List[Dict]:
    """
    运行Step 5: 主题聚类
    
    Args:
        clips_with_titles_path: 带标题的片段文件路径
        output_path: 输出文件路径
        prompt_files: 自定义提示词文件
        
    Returns:
        合集数据
    """
    # 加载数据
    with open(clips_with_titles_path, 'r', encoding='utf-8') as f:
        clips_with_titles = json.load(f)
    
    # 创建聚类器
    if metadata_dir is None:
        metadata_dir = METADATA_DIR
    clusterer = ClusteringEngine(metadata_dir=Path(metadata_dir), prompt_files=prompt_files)
    
    # 进行聚类
    collections_data = clusterer.cluster_clips(clips_with_titles)
    
    # 保存结果
    if output_path is None:
        if metadata_dir is None:
            metadata_dir = METADATA_DIR
        output_path = Path(metadata_dir) / "step5_collections.json"
    
    clusterer.save_collections(collections_data, output_path)
    
    return collections_data
