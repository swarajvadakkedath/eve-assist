"""VisionPipeline — orchestrates screen capture → analysis → structured observation."""

from aios.conversation.manager import ConversationManager
from aios.vision.models import VisionConfig, VisionObservation
from aios.vision.session import VisionSession
from aios.vision.events import VisionEventPublisher


class VisionPipeline:
    """Full vision pipeline: screen → vision engine → structured observation → conversation manager."""

    def __init__(
        self,
        vision_session: VisionSession,
        conversation_manager: ConversationManager,
        event_publisher: VisionEventPublisher | None = None,
        config: VisionConfig | None = None,
    ):
        self.session = vision_session
        self.conversation_manager = conversation_manager
        self.event_publisher = event_publisher or VisionEventPublisher()
        self.config = config or VisionConfig()

    async def observe_screen(self, session_id: str, conversation_id: str | None = None) -> VisionObservation:
        await self.event_publisher.publish_capture_start()
        await self.event_publisher.publish_analysis_start()
        observation = await self.session.analyze_current_screen()
        await self.event_publisher.publish_capture_complete(size=len(observation.screenshot.image_data) if observation.screenshot else 0)
        await self.event_publisher.publish_analysis_complete(
            element_count=len(observation.detection.elements) if observation.detection else 0,
        )
        await self.event_publisher.publish_observation(observation.to_dict())
        await self._feed_to_conversation(observation, conversation_id)
        return observation

    async def observe_image(self, session_id: str, image_data: bytes, conversation_id: str | None = None) -> VisionObservation:
        await self.event_publisher.publish_analysis_start(source="upload")
        observation = await self.session.analyze_uploaded_image(image_data)
        await self.event_publisher.publish_analysis_complete(
            source="upload",
            element_count=len(observation.detection.elements) if observation.detection else 0,
        )
        await self.event_publisher.publish_observation(observation.to_dict())
        await self._feed_to_conversation(observation, conversation_id)
        return observation

    async def _feed_to_conversation(self, observation: VisionObservation, conversation_id: str | None = None):
        """Feed structured observation into the conversation as untrusted context."""
        if not self.conversation_manager or not conversation_id:
            return
        structured = observation.to_structured()
        await self.conversation_manager.add_vision_observation(
            conversation_id=conversation_id,
            observation=structured,
        )
