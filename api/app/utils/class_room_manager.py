from config.utils.storage_manager import CloudStorageManager
from core.models import UserModel
from ai.utils.synchronize_manager import SynchronizeManager
from app.models import ClassRoomModel, ClassRoomMemberModel, ClassRoomContentModel

class ClassRoomManager:
    def __init__(self, instructions="", teaching_tasks=[]):
        self.class_room = None
        self.teaching_tasks = teaching_tasks
        self.instructions = instructions

    def build_a_room(self, title, description, teacher_voice_name, language):
        cur_room = ClassRoomModel()
        cur_room.course_title = title
        cur_room.course_description = description
        cur_room.teacher_voice_name = teacher_voice_name
        cur_room.language = language
        cur_room.save()
        self.class_room = cur_room
        return cur_room

    def add_member_to_room(self, user_email):
        if self.class_room is None:
            raise ValueError("No class room exists.")
        cur_user = UserModel.objects.filter(email=user_email).first()
        if not cur_user:
            raise ValueError("User does not exist.")
        member = cur_user
        member_exist = ClassRoomMemberModel.objects.filter(class_room=self.class_room, user__email=user_email).exists()
        if member_exist:
            raise ValueError("Member already in the room.")
        cur_class_room_member = ClassRoomMemberModel()
        cur_class_room_member.class_room = self.class_room
        cur_class_room_member.user = member
        cur_class_room_member.save()
        return cur_class_room_member

    def remove_member_from_room(self, room, user_email):
        if self.class_room is None:
            raise ValueError("No class room exists.")
        cur_user = UserModel.objects.filter(email=user_email).first()
        if not cur_user:
            raise ValueError("User does not exist.")
        member_exist = ClassRoomMemberModel.objects.filter(class_room=self.class_room, user__email=user_email).exists()
        if not member_exist:
            raise ValueError("Member not found in the room.")
        cur_class_room_member = ClassRoomMemberModel.objects.filter(class_room=self.class_room, user__email=user_email).first()
        cur_class_room_member.delete()
        return cur_class_room_member
    
    def get_room_members(self):
        if self.class_room is None:
            raise ValueError("No class room exists.")
        return ClassRoomMemberModel.objects.filter(class_room=self.class_room).select_related('user')
    
    
    def build_teaching_contents(self):
        if self.class_room is None:
            raise ValueError("No class room exists.")
        created_contents = []
        for idx, task in enumerate(self.teaching_tasks):
            print(f"Building content for task {idx+1}: {task.get('title', 'No Title')}")
            content = ClassRoomContentModel()
            content.class_room = self.class_room
            content.title = task.get("title", f"Content {idx+1}")
            content.order = idx + 1
            prompt = task.get("prompt", "")
            instructions = (
                f"{self.instructions}\n"
                f"Based on the following prompt, create detailed teaching content with examples and explanations:\n"
                f"Prompt: {prompt}\n"
                f"Ensure the content is clear, engaging, and suitable for beginners.\n"
            )
            sync_manager = SynchronizeManager()
            result = sync_manager.full_synchronization_pipeline(instructions)
            audio_base64 = result.get("audio_base64", "")
            storage = CloudStorageManager()
            audio_file_key = storage.upload_base64(audio_base64, bucket="AI", file_key=f"teachers/{self.class_room.uuid}/{idx + 1}.wav", acl="public-read")
            slides = result.get("slide_alignment", [])
            ssml = result.get("ssml", "")
            audio_length_sec = result.get("audio_length_sec", 0)
            content.slides = slides
            content.ssml = ssml
            content.audio_length_sec = audio_length_sec
            content.audio_file = audio_file_key
            content.save()
            created_contents.append(content)
        return created_contents