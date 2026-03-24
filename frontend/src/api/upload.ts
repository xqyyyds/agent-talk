import request from "./request";

type UploadAvatarResponse = {
  avatar: string;
};

type ApiResponse<T> = {
  code: number;
  message?: string;
  data?: T;
};

export function uploadAvatar(file: File) {
  const formData = new FormData();
  formData.append("file", file);
  return request.post<ApiResponse<UploadAvatarResponse>>(
    "/upload/avatar",
    formData,
    {
      timeout: 180000,
    },
  );
}
