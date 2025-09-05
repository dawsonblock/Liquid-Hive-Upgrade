"""Dynamic prompt patching system for continuous improvement."""

import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
import structlog

logger = structlog.get_logger(__name__)


class PatchType(str, Enum):
    """Types of prompt patches."""
    CONCISENESS_OPTIMIZATION = "conciseness_optimization"
    SATISFACTION_ENHANCEMENT = "satisfaction_enhancement"
    ACCURACY_IMPROVEMENT = "accuracy_improvement"
    CLARITY_ENHANCEMENT = "clarity_enhancement"
    PERFORMANCE_OPTIMIZATION = "performance_optimization"
    SAFETY_ENHANCEMENT = "safety_enhancement"
    DOMAIN_ADAPTATION = "domain_adaptation"


@dataclass
class PromptPatch:
    """Represents a prompt modification patch."""
    
    # Identity
    patch_id: str
    patch_type: PatchType
    target: str  # Agent or prompt identifier
    
    # Content
    description: str
    changes: List[str]  # List of changes to apply
    original_version: Optional[str] = None
    patched_version: Optional[str] = None
    
    # Configuration
    priority: int = 5  # 1-10, higher = more important
    active: bool = True
    experimental: bool = False
    
    # Metadata
    created_at: datetime = None
    created_by: str = "oracle_system"
    version: str = "1.0"
    tags: List[str] = None
    metadata: Dict[str, Any] = None
    
    # Performance tracking
    applications: int = 0
    success_rate: float = 0.0
    avg_improvement: float = 0.0
    user_feedback_score: Optional[float] = None
    
    def __post_init__(self):
        """Initialize default values."""
        if self.created_at is None:
            self.created_at = datetime.utcnow()
        if self.tags is None:
            self.tags = []
        if self.metadata is None:
            self.metadata = {}
        if not self.patch_id:
            self.patch_id = f"patch_{uuid.uuid4().hex[:8]}"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        data = asdict(self)
        data['patch_type'] = self.patch_type.value
        data['created_at'] = self.created_at.isoformat()
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PromptPatch":
        """Create from dictionary representation."""
        data['patch_type'] = PatchType(data['patch_type'])
        data['created_at'] = datetime.fromisoformat(data['created_at'])
        return cls(**data)


class PromptTemplate:
    """Manages a versioned prompt template with patch history."""
    
    def __init__(
        self,
        template_id: str,
        name: str,
        base_template: str,
        variables: Optional[List[str]] = None
    ):
        """Initialize prompt template.
        
        Args:
            template_id: Unique identifier
            name: Human-readable name
            base_template: Base template content
            variables: List of template variables
        """
        self.template_id = template_id
        self.name = name
        self.base_template = base_template
        self.variables = variables or []
        
        # Version management
        self.current_version = 1
        self.version_history = {1: base_template}
        self.applied_patches: List[str] = []  # Patch IDs
        
        # Performance tracking
        self.usage_count = 0
        self.success_metrics = {}
        self.last_used = None
        
    def apply_patch(self, patch: PromptPatch) -> bool:
        """Apply a patch to this template.
        
        Args:
            patch: Patch to apply
            
        Returns:
            True if patch was applied successfully
        """
        try:
            if patch.patch_id in self.applied_patches:
                logger.warning("Patch already applied", patch_id=patch.patch_id)
                return False
            
            # Get current template content
            current_content = self.version_history[self.current_version]
            
            # Apply patch changes
            patched_content = self._apply_patch_changes(current_content, patch)
            
            if patched_content != current_content:
                # Create new version
                self.current_version += 1
                self.version_history[self.current_version] = patched_content
                self.applied_patches.append(patch.patch_id)
                
                logger.info(
                    "Prompt patch applied",
                    template_id=self.template_id,
                    patch_id=patch.patch_id,
                    new_version=self.current_version
                )
                
                return True
            else:
                logger.info("Patch resulted in no changes", patch_id=patch.patch_id)
                return False
                
        except Exception as e:
            logger.error("Error applying patch", patch_id=patch.patch_id, error=str(e))
            return False
    
    def _apply_patch_changes(self, content: str, patch: PromptPatch) -> str:
        """Apply patch changes to content.
        
        Args:
            content: Current content
            patch: Patch to apply
            
        Returns:
            Modified content
        """
        patched_content = content
        
        for change in patch.changes:
            if change.startswith("Add explicit instructions"):
                # Add clarity instructions
                instruction = "\n\nPlease provide clear, concise responses with specific examples where appropriate."
                if instruction not in patched_content:
                    patched_content += instruction
                    
            elif change.startswith("Remove unnecessary context"):
                # Remove verbose context (simplified)
                lines = patched_content.split('\n')
                filtered_lines = [line for line in lines if not line.startswith("Note:")]
                patched_content = '\n'.join(filtered_lines)
                
            elif change.startswith("Add timeout guidance"):
                # Add performance guidance
                guidance = "\n\nFor complex requests, aim to respond within 30 seconds."
                if guidance not in patched_content:
                    patched_content += guidance
                    
            elif change.startswith("Add more empathetic language"):
                # Add empathy markers
                if "I understand" not in patched_content:
                    patched_content = "I understand you're looking for help with this. " + patched_content
                    
            elif change.startswith("Include clarification questions"):
                # Add clarification prompts
                clarification = "\n\nIf any aspect is unclear, I'll ask for clarification to provide the most helpful response."
                if clarification not in patched_content:
                    patched_content += clarification
                    
            elif change.startswith("Provide more detailed explanations"):
                # Add detail instruction
                detail_instruction = "\n\nI'll provide detailed explanations with step-by-step reasoning when appropriate."
                if detail_instruction not in patched_content:
                    patched_content += detail_instruction
                    
            elif change.startswith("Add confidence indicators"):
                # Add confidence markers
                confidence_instruction = "\n\nI'll indicate my confidence level and mention when I'm uncertain about specific aspects."
                if confidence_instruction not in patched_content:
                    patched_content += confidence_instruction
        
        return patched_content
    
    def rollback_to_version(self, version: int) -> bool:
        """Rollback to a specific version.
        
        Args:
            version: Version number to rollback to
            
        Returns:
            True if rollback was successful
        """
        try:
            if version not in self.version_history:
                logger.error("Version not found", version=version, template_id=self.template_id)
                return False
            
            old_version = self.current_version
            self.current_version = version
            
            # Remove patches that were applied after this version
            # (Simplified - in practice would need more sophisticated patch tracking)
            
            logger.info(
                "Template rolled back",
                template_id=self.template_id,
                from_version=old_version,
                to_version=version
            )
            
            return True
            
        except Exception as e:
            logger.error("Error rolling back template", error=str(e))
            return False
    
    def get_current_content(self) -> str:
        """Get current template content.
        
        Returns:
            Current template content
        """
        return self.version_history[self.current_version]
    
    def get_version_info(self) -> Dict[str, Any]:
        """Get version information.
        
        Returns:
            Dictionary with version information
        """
        return {
            "template_id": self.template_id,
            "name": self.name,
            "current_version": self.current_version,
            "total_versions": len(self.version_history),
            "applied_patches": len(self.applied_patches),
            "usage_count": self.usage_count,
            "last_used": self.last_used.isoformat() if self.last_used else None,
            "variables": self.variables
        }


class PromptsPatcher:
    """Main system for managing prompt patches and templates."""
    
    def __init__(self, templates_path: str = "./templates"):
        """Initialize the prompts patcher.
        
        Args:
            templates_path: Path to store prompt templates
        """
        self.templates_path = Path(templates_path)
        self.templates_path.mkdir(parents=True, exist_ok=True)
        
        # Storage
        self.templates: Dict[str, PromptTemplate] = {}
        self.patches: Dict[str, PromptPatch] = {}
        
        # Statistics
        self.patcher_stats = {
            "patches_created": 0,
            "patches_applied": 0,
            "templates_modified": 0,
            "rollbacks_performed": 0,
            "avg_improvement": 0.0
        }
        
        logger.info("PromptsPatcher initialized", templates_path=str(self.templates_path))
        
        # Load existing templates and patches
        self._load_templates()
        self._load_patches()
    
    def _load_templates(self):
        """Load existing templates from storage."""
        try:
            templates_file = self.templates_path / "templates.json"
            
            if templates_file.exists():
                with open(templates_file, 'r') as f:
                    templates_data = json.load(f)
                
                for template_data in templates_data:
                    template = PromptTemplate(
                        template_id=template_data["template_id"],
                        name=template_data["name"],
                        base_template=template_data["base_template"],
                        variables=template_data.get("variables", [])
                    )
                    
                    # Restore state
                    template.current_version = template_data.get("current_version", 1)
                    template.version_history = template_data.get("version_history", {1: template.base_template})
                    template.applied_patches = template_data.get("applied_patches", [])
                    template.usage_count = template_data.get("usage_count", 0)
                    
                    self.templates[template.template_id] = template
                
                logger.info("Templates loaded", count=len(self.templates))
            else:
                # Create default templates
                self._create_default_templates()
                
        except Exception as e:
            logger.error("Error loading templates", error=str(e))
            self._create_default_templates()
    
    def _create_default_templates(self):
        """Create default prompt templates."""
        default_templates = [
            {
                "template_id": "general_assistant",
                "name": "General Assistant",
                "base_template": """You are a helpful AI assistant. Please provide accurate, helpful, and concise responses to user queries.

User Query: {query}

Please respond with:
1. A clear, direct answer
2. Relevant context or explanation
3. Any important caveats or limitations""",
                "variables": ["query"]
            },
            {
                "template_id": "coding_assistant",
                "name": "Coding Assistant", 
                "base_template": """You are an expert programming assistant. Help users with coding questions, debugging, and best practices.

Programming Request: {request}
Language: {language}

Please provide:
1. Working code solution
2. Clear explanation of the approach
3. Best practices and potential improvements
4. Testing suggestions if applicable""",
                "variables": ["request", "language"]
            },
            {
                "template_id": "analytical_assistant",
                "name": "Analytical Assistant",
                "base_template": """You are an analytical AI assistant specializing in data analysis and problem-solving.

Analysis Request: {request}
Context: {context}

Please provide:
1. Structured analysis of the problem
2. Key insights and patterns
3. Recommendations with reasoning
4. Potential limitations or assumptions""",
                "variables": ["request", "context"]
            }
        ]
        
        for template_data in default_templates:
            template = PromptTemplate(
                template_id=template_data["template_id"],
                name=template_data["name"],
                base_template=template_data["base_template"],
                variables=template_data["variables"]
            )
            self.templates[template.template_id] = template
        
        logger.info("Default templates created", count=len(default_templates))
    
    def _load_patches(self):
        """Load existing patches from storage."""
        try:
            patches_file = self.templates_path / "patches.json"
            
            if patches_file.exists():
                with open(patches_file, 'r') as f:
                    patches_data = json.load(f)
                
                for patch_data in patches_data:
                    patch = PromptPatch.from_dict(patch_data)
                    self.patches[patch.patch_id] = patch
                
                logger.info("Patches loaded", count=len(self.patches))
                
        except Exception as e:
            logger.error("Error loading patches", error=str(e))
    
    async def patch_prompt(
        self, 
        target: str, 
        patch_type: PatchType,
        description: str,
        changes: List[str],
        priority: int = 5,
        experimental: bool = False,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Apply a patch to a prompt template.
        
        Args:
            target: Target template or agent identifier
            patch_type: Type of patch to apply
            description: Description of the patch
            changes: List of changes to apply
            priority: Patch priority (1-10)
            experimental: Whether this is an experimental patch
            metadata: Additional metadata
            
        Returns:
            True if patch was applied successfully
        """
        try:
            # Find target template
            if target not in self.templates:
                logger.error("Target template not found", target=target)
                return False
            
            # Create patch
            patch = PromptPatch(
                patch_id=f"patch_{uuid.uuid4().hex[:8]}",
                patch_type=patch_type,
                target=target,
                description=description,
                changes=changes,
                priority=priority,
                experimental=experimental,
                metadata=metadata or {}
            )
            
            # Apply patch to template
            template = self.templates[target]
            success = template.apply_patch(patch)
            
            if success:
                # Store patch
                self.patches[patch.patch_id] = patch
                
                # Update patch performance
                patch.applications += 1
                
                # Update statistics
                self.patcher_stats["patches_created"] += 1
                self.patcher_stats["patches_applied"] += 1
                self.patcher_stats["templates_modified"] += 1
                
                # Save changes
                await self._save_templates()
                await self._save_patches()
                
                logger.info(
                    "Prompt patch applied successfully",
                    target=target,
                    patch_id=patch.patch_id,
                    patch_type=patch_type.value
                )
                
                return True
            
            return False
            
        except Exception as e:
            logger.error("Error applying prompt patch", error=str(e))
            return False
    
    async def rollback_patch(self, target: str, patch_id: str) -> bool:
        """Rollback a specific patch from a template.
        
        Args:
            target: Target template identifier
            patch_id: Patch ID to rollback
            
        Returns:
            True if rollback was successful
        """
        try:
            if target not in self.templates:
                logger.error("Target template not found", target=target)
                return False
            
            template = self.templates[target]
            
            if patch_id not in template.applied_patches:
                logger.warning("Patch not applied to template", patch_id=patch_id, target=target)
                return False
            
            # Find version before this patch was applied (simplified)
            # In practice, would need more sophisticated patch dependency tracking
            patch_index = template.applied_patches.index(patch_id)
            
            if patch_index == 0:
                # Rollback to base version
                rollback_version = 1
            else:
                # Rollback to previous patch
                rollback_version = patch_index + 1
            
            success = template.rollback_to_version(rollback_version)
            
            if success:
                # Remove patch from applied list
                template.applied_patches.remove(patch_id)
                
                # Update statistics
                self.patcher_stats["rollbacks_performed"] += 1
                
                # Save changes
                await self._save_templates()
                
                logger.info(
                    "Patch rolled back successfully",
                    target=target,
                    patch_id=patch_id,
                    rollback_version=rollback_version
                )
                
                return True
            
            return False
            
        except Exception as e:
            logger.error("Error rolling back patch", error=str(e))
            return False
    
    async def get_template(self, template_id: str) -> Optional[PromptTemplate]:
        """Get a prompt template by ID.
        
        Args:
            template_id: Template identifier
            
        Returns:
            PromptTemplate if found, None otherwise
        """
        return self.templates.get(template_id)
    
    async def list_templates(self) -> Dict[str, Dict[str, Any]]:
        """List all available templates.
        
        Returns:
            Dictionary mapping template IDs to template info
        """
        return {
            template_id: template.get_version_info()
            for template_id, template in self.templates.items()
        }
    
    async def list_patches(self, target: Optional[str] = None) -> Dict[str, Dict[str, Any]]:
        """List patches, optionally filtered by target.
        
        Args:
            target: Optional target filter
            
        Returns:
            Dictionary mapping patch IDs to patch info
        """
        patches = {}
        
        for patch_id, patch in self.patches.items():
            if target is None or patch.target == target:
                patches[patch_id] = patch.to_dict()
        
        return patches
    
    async def get_patch_performance(self, patch_id: str) -> Dict[str, Any]:
        """Get performance metrics for a specific patch.
        
        Args:
            patch_id: Patch identifier
            
        Returns:
            Dictionary with performance metrics
        """
        if patch_id not in self.patches:
            return {"error": "Patch not found"}
        
        patch = self.patches[patch_id]
        
        return {
            "patch_id": patch_id,
            "applications": patch.applications,
            "success_rate": patch.success_rate,
            "avg_improvement": patch.avg_improvement,
            "user_feedback_score": patch.user_feedback_score,
            "active": patch.active,
            "experimental": patch.experimental,
            "created_at": patch.created_at.isoformat(),
            "patch_type": patch.patch_type.value,
            "target": patch.target
        }
    
    async def update_patch_performance(
        self,
        patch_id: str,
        success: bool,
        improvement: Optional[float] = None,
        user_feedback: Optional[float] = None
    ):
        """Update performance metrics for a patch.
        
        Args:
            patch_id: Patch identifier
            success: Whether the patch application was successful
            improvement: Measured improvement (0-1 scale)
            user_feedback: User feedback score (0-5 scale)
        """
        try:
            if patch_id not in self.patches:
                logger.warning("Patch not found for performance update", patch_id=patch_id)
                return
            
            patch = self.patches[patch_id]
            
            # Update success rate (exponential moving average)
            if patch.applications > 0:
                alpha = 0.1  # Smoothing factor
                patch.success_rate = alpha * (1.0 if success else 0.0) + (1 - alpha) * patch.success_rate
            else:
                patch.success_rate = 1.0 if success else 0.0
            
            # Update improvement metric
            if improvement is not None:
                if patch.avg_improvement == 0.0:
                    patch.avg_improvement = improvement
                else:
                    alpha = 0.1
                    patch.avg_improvement = alpha * improvement + (1 - alpha) * patch.avg_improvement
            
            # Update user feedback
            if user_feedback is not None:
                patch.user_feedback_score = user_feedback
            
            # Update global statistics
            if improvement is not None and improvement > 0:
                current_avg = self.patcher_stats["avg_improvement"]
                if current_avg == 0.0:
                    self.patcher_stats["avg_improvement"] = improvement
                else:
                    alpha = 0.05  # Slower update for global average
                    self.patcher_stats["avg_improvement"] = alpha * improvement + (1 - alpha) * current_avg
            
            await self._save_patches()
            
            logger.debug(
                "Patch performance updated",
                patch_id=patch_id,
                success=success,
                improvement=improvement,
                user_feedback=user_feedback
            )
            
        except Exception as e:
            logger.error("Error updating patch performance", error=str(e))
    
    async def _save_templates(self):
        """Save templates to storage."""
        try:
            templates_data = []
            
            for template in self.templates.values():
                data = {
                    "template_id": template.template_id,
                    "name": template.name,
                    "base_template": template.base_template,
                    "variables": template.variables,
                    "current_version": template.current_version,
                    "version_history": template.version_history,
                    "applied_patches": template.applied_patches,
                    "usage_count": template.usage_count
                }
                templates_data.append(data)
            
            templates_file = self.templates_path / "templates.json"
            with open(templates_file, 'w') as f:
                json.dump(templates_data, f, indent=2, default=str)
            
            logger.debug("Templates saved", count=len(templates_data))
            
        except Exception as e:
            logger.error("Error saving templates", error=str(e))
    
    async def _save_patches(self):
        """Save patches to storage."""
        try:
            patches_data = [patch.to_dict() for patch in self.patches.values()]
            
            patches_file = self.templates_path / "patches.json"
            with open(patches_file, 'w') as f:
                json.dump(patches_data, f, indent=2, default=str)
            
            logger.debug("Patches saved", count=len(patches_data))
            
        except Exception as e:
            logger.error("Error saving patches", error=str(e))
    
    async def get_status(self) -> Dict[str, Any]:
        """Get comprehensive patcher system status.
        
        Returns:
            Dictionary with system status information
        """
        try:
            return {
                "templates_path": str(self.templates_path),
                "total_templates": len(self.templates),
                "total_patches": len(self.patches),
                "active_patches": len([p for p in self.patches.values() if p.active]),
                "experimental_patches": len([p for p in self.patches.values() if p.experimental]),
                "statistics": self.patcher_stats,
                "template_usage": {
                    tid: template.usage_count 
                    for tid, template in self.templates.items()
                },
                "patch_types": {
                    patch_type.value: len([
                        p for p in self.patches.values() 
                        if p.patch_type == patch_type
                    ])
                    for patch_type in PatchType
                }
            }
            
        except Exception as e:
            logger.error("Error getting patcher status", error=str(e))
            return {"error": str(e)}