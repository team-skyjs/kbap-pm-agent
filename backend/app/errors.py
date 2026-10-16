from fastapi.responses import JSONResponse


class ApiError(Exception):
    def __init__(self, status: int, code: str, message: str):
        self.status, self.code, self.message = status, code, message


def err(status: int, code: str, message: str) -> JSONResponse:
    return JSONResponse({"error": {"code": code, "message": message}}, status_code=status)


class ToolError(Exception):
    """메시지가 그대로 도구 실패 결과가 되는 예외(모델이 읽고 고쳐 다시 부를 수 있게 머리말 없이)"""
