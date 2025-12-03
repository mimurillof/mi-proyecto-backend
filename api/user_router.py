from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from crud.user_service import user_crud
from models.schemas import (
    UserResponse, 
    APIResponse, 
    UserProfileResponse, 
    UserProfileUpdate,
    UserAvatarResponse
)
from auth.dependencies import get_current_user
from db_models.models import User
from services.user_profile_service import get_user_profile_service

router = APIRouter()


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: User = Depends(get_current_user)
):
    """Get current authenticated user information (basic)"""
    return current_user


@router.get("/profile", response_model=UserProfileResponse)
async def get_user_profile(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Obtiene el perfil completo del usuario autenticado.
    
    Incluye:
    - Información personal (nombre, apellido, email)
    - Datos adicionales (móvil, país, identificación, bio)
    - URL de la imagen de perfil (firmada si existe, o avatar por defecto)
    """
    profile_service = get_user_profile_service()
    
    # Obtener URL de imagen de perfil
    gender_value = current_user.gender.value if current_user.gender else None
    profile_image_url, is_default = await profile_service.get_profile_image_url(
        user_id=str(current_user.user_id),
        profile_image_path=current_user.profile_image_path,
        gender=gender_value,
        first_name=current_user.first_name
    )
    
    # Construir respuesta de perfil
    return UserProfileResponse(
        user_id=current_user.user_id,
        email=current_user.email,
        first_name=current_user.first_name,
        last_name=current_user.last_name,
        birth_date=current_user.birth_date,
        gender=current_user.gender,
        mobile=current_user.mobile,
        country=current_user.country,
        identification_number=current_user.identification_number,
        bio=current_user.bio,
        profile_image_url=profile_image_url,
        created_at=current_user.created_at,
        has_completed_onboarding=current_user.has_completed_onboarding or False
    )


@router.put("/profile", response_model=UserProfileResponse)
async def update_user_profile(
    profile_data: UserProfileUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Actualiza el perfil del usuario autenticado.
    
    Campos actualizables:
    - first_name, last_name
    - birth_date, gender
    - mobile, country, identification_number
    - bio
    """
    # Actualizar perfil en BD
    updated_user = await user_crud.update_user_profile(
        db=db,
        user_id=current_user.user_id,
        profile_data=profile_data
    )
    
    if not updated_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuario no encontrado"
        )
    
    # Obtener URL de imagen de perfil para la respuesta
    profile_service = get_user_profile_service()
    gender_value = updated_user.gender.value if updated_user.gender else None
    profile_image_url, _ = await profile_service.get_profile_image_url(
        user_id=str(updated_user.user_id),
        profile_image_path=updated_user.profile_image_path,
        gender=gender_value,
        first_name=updated_user.first_name
    )
    
    return UserProfileResponse(
        user_id=updated_user.user_id,
        email=updated_user.email,
        first_name=updated_user.first_name,
        last_name=updated_user.last_name,
        birth_date=updated_user.birth_date,
        gender=updated_user.gender,
        mobile=updated_user.mobile,
        country=updated_user.country,
        identification_number=updated_user.identification_number,
        bio=updated_user.bio,
        profile_image_url=profile_image_url,
        created_at=updated_user.created_at,
        has_completed_onboarding=updated_user.has_completed_onboarding or False
    )


@router.get("/profile/avatar", response_model=UserAvatarResponse)
async def get_user_avatar(
    current_user: User = Depends(get_current_user)
):
    """
    Obtiene la URL del avatar/imagen de perfil del usuario.
    
    - Si el usuario tiene imagen de perfil en Storage, retorna URL firmada
    - Si no tiene imagen, retorna avatar por defecto según género
    """
    profile_service = get_user_profile_service()
    
    gender_value = current_user.gender.value if current_user.gender else None
    avatar_url, is_default = await profile_service.get_profile_image_url(
        user_id=str(current_user.user_id),
        profile_image_path=current_user.profile_image_path,
        gender=gender_value,
        first_name=current_user.first_name
    )
    
    return UserAvatarResponse(
        avatar_url=avatar_url,
        is_default=is_default,
        gender=current_user.gender
    )


@router.post("/profile/avatar", response_model=APIResponse)
async def upload_profile_avatar(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Sube una nueva imagen de perfil para el usuario.
    
    - Formatos permitidos: JPG, JPEG, PNG, GIF, WEBP
    - Tamaño máximo: 5MB
    - Reemplaza la imagen anterior si existe
    """
    profile_service = get_user_profile_service()
    
    # Leer contenido del archivo
    file_content = await file.read()
    
    # Subir imagen a Storage
    result = await profile_service.upload_profile_image(
        user_id=str(current_user.user_id),
        file_content=file_content,
        content_type=file.content_type or "image/jpeg",
        filename=file.filename or "profile.jpg"
    )
    
    if not result.get("success"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result.get("message", "Error al subir imagen")
        )
    
    # Actualizar path en la BD
    image_path = result.get("path")
    await user_crud.update_profile_image_path(
        db=db,
        user_id=current_user.user_id,
        image_path=image_path
    )
    
    return APIResponse(
        success=True,
        message="Imagen de perfil actualizada correctamente",
        data={"path": image_path}
    )


@router.delete("/profile/avatar", response_model=APIResponse)
async def delete_profile_avatar(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Elimina la imagen de perfil del usuario.
    
    Después de eliminar, el usuario verá el avatar por defecto.
    """
    profile_service = get_user_profile_service()
    
    # Eliminar imagen de Storage
    result = await profile_service.delete_profile_image(str(current_user.user_id))
    
    if not result.get("success"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result.get("message", "Error al eliminar imagen")
        )
    
    # Limpiar path en la BD
    await user_crud.update_profile_image_path(
        db=db,
        user_id=current_user.user_id,
        image_path=None
    )
    
    return APIResponse(
        success=True,
        message="Imagen de perfil eliminada correctamente"
    )


@router.post("/profile/complete-onboarding", response_model=APIResponse)
async def complete_onboarding(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Marca el onboarding del usuario como completado.
    """
    updated_user = await user_crud.mark_onboarding_complete(
        db=db,
        user_id=current_user.user_id
    )
    
    if not updated_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuario no encontrado"
        )
    
    return APIResponse(
        success=True,
        message="Onboarding completado correctamente"
    ) 
