# SeaPoint tide cache update. Windows PowerShell 5.1 compatible.
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version 2.0
$utf8 = New-Object System.Text.UTF8Encoding($false, $true)
# Windows PowerShell 5.1 returns a top-level JSON array as one pipeline
# object. Assign that result first, then enumerate the variable explicitly.
$definitionJson = $utf8.GetString([Convert]::FromBase64String('W3sicGF0aCI6ImxpYi9tYWluLmRhcnQiLCJiYWNrdXBfbmFtZSI6Im1haW4uZGFydC5iYWsiLCJtYXJrZXJzIjpbImNsYXNzIE1hcmluZURhc2hib2FyZCBleHRlbmRzIFN0YXRlZnVsV2lkZ2V0IiwiY2xhc3MgX01hcmluZURhc2hib2FyZFN0YXRlIiwiRnV0dXJlPHZvaWQ+IGZldGNoVGlkZXMoIl0sInBhdGNoZXMiOlt7Im5hbWUiOiJ0aWRlLWNhY2hlLTEiLCJvbGQiOiJpbXBvcnQgJ3dlYXRoZXJfc3lub3BzaXMuZGFydCc7XG5pbXBvcnQgJ29mZmljaWFsX3dlYXRoZXJfY2FyZC5kYXJ0JztcbmltcG9ydCAnb2ZmaWNpYWxfYWxlcnRfZmVlZC5kYXJ0Jztcblxudm9pZCBtYWluKCkge1xuICBydW5BcHAoY29uc3QgU2VhUG9pbnRBcHAoKSk7XG4iLCJuZXciOiJpbXBvcnQgJ3dlYXRoZXJfc3lub3BzaXMuZGFydCc7XG5pbXBvcnQgJ29mZmljaWFsX3dlYXRoZXJfY2FyZC5kYXJ0JztcbmltcG9ydCAnb2ZmaWNpYWxfYWxlcnRfZmVlZC5kYXJ0JztcbmltcG9ydCAndGlkZV9wcmVkaWN0aW9ucy5kYXJ0Jztcblxudm9pZCBtYWluKCkge1xuICBydW5BcHAoY29uc3QgU2VhUG9pbnRBcHAoKSk7XG4ifSx7Im5hbWUiOiJ0aWRlLWNhY2hlLTIiLCJvbGQiOiJcbiAgc3RhdGljIGNvbnN0IER1cmF0aW9uIF9mb3JlY2FzdEludGVydmFsID0gRHVyYXRpb24oaG91cnM6IDEpO1xuICBzdGF0aWMgY29uc3QgRHVyYXRpb24gX3dhcm5pbmdJbnRlcnZhbCA9IER1cmF0aW9uKG1pbnV0ZXM6IDE1KTtcbiAgc3RhdGljIGNvbnN0IER1cmF0aW9uIF90aWRlSW50ZXJ2YWwgPSBEdXJhdGlvbihob3VyczogNik7XG4gIHN0YXRpYyBjb25zdCBEdXJhdGlvbiBfb2ZmaWNpYWxUZW1wZXJhdHVyZUludGVydmFsID0gRHVyYXRpb24oaG91cnM6IDMpO1xuICBzdGF0aWMgY29uc3QgRHVyYXRpb24gX3JldHJ5SW50ZXJ2YWwgPSBEdXJhdGlvbihtaW51dGVzOiAxMCk7XG5cbiIsIm5ldyI6IlxuICBzdGF0aWMgY29uc3QgRHVyYXRpb24gX2ZvcmVjYXN0SW50ZXJ2YWwgPSBEdXJhdGlvbihob3VyczogMSk7XG4gIHN0YXRpYyBjb25zdCBEdXJhdGlvbiBfd2FybmluZ0ludGVydmFsID0gRHVyYXRpb24obWludXRlczogMTUpO1xuICBmaW5hbCBfdGlkZUNsaWVudCA9IFRpZGVQcmVkaWN0aW9uQ2xpZW50KCk7XG4gIFN0cmluZz8gX3RpZGVOb3RpY2U7XG4gIHN0YXRpYyBjb25zdCBEdXJhdGlvbiBfb2ZmaWNpYWxUZW1wZXJhdHVyZUludGVydmFsID0gRHVyYXRpb24oaG91cnM6IDMpO1xuICBzdGF0aWMgY29uc3QgRHVyYXRpb24gX3JldHJ5SW50ZXJ2YWwgPSBEdXJhdGlvbihtaW51dGVzOiAxMCk7XG5cbiJ9LHsibmFtZSI6InRpZGUtY2FjaGUtMyIsIm9sZCI6IiAgICAgIHRhc2tzLmFkZChmZXRjaE9mZmljaWFsQWxlcnRzKCkpO1xuICAgIH1cblxuICAgIGlmIChmb3JjZSB8fFxuICAgICAgICBfZHVlKFxuICAgICAgICAgIF90aWRlc0NoZWNrZWQsXG4gICAgICAgICAgX2xhc3RUaWRlc0F0dGVtcHQsXG4gICAgICAgICAgX3RpZGVJbnRlcnZhbCxcbiAgICAgICAgKSkge1xuICAgICAgX2xhc3RUaWRlc0F0dGVtcHQgPSBub3c7XG4gICAgICB0YXNrcy5hZGQoZmV0Y2hUaWRlcygpKTtcbiAgICB9XG5cbiAgICBpZiAoZm9yY2UgfHxcbiIsIm5ldyI6IiAgICAgIHRhc2tzLmFkZChmZXRjaE9mZmljaWFsQWxlcnRzKCkpO1xuICAgIH1cblxuICAgIGlmIChmb3JjZSB8fCBzaG91bGRDaGVja1RpZGVzKFxuICAgICAgbm93OiBub3csIGNoZWNrZWRBdDogX3RpZGVzQ2hlY2tlZCwgYXR0ZW1wdGVkQXQ6IF9sYXN0VGlkZXNBdHRlbXB0LFxuICAgICkpIHtcbiAgICAgIF9sYXN0VGlkZXNBdHRlbXB0ID0gbm93O1xuICAgICAgdGFza3MuYWRkKGZldGNoVGlkZXMocmV0cnlQYXVzZWQ6IGZvcmNlKSk7XG4gICAgfVxuXG4gICAgaWYgKGZvcmNlIHx8XG4ifSx7Im5hbWUiOiJ0aWRlLWNhY2hlLTQiLCJvbGQiOiIgICAgfVxuICB9XG5cbiAgRnV0dXJlPHZvaWQ+IGZldGNoVGlkZXMoKSBhc3luYyB7XG4gICAgdHJ5IHtcbiAgICAgIGZpbmFsIHJlcXVlc3RlZENhY2hlS2V5ID0gX3RpZGVDYWNoZUtleTtcblxuIiwibmV3IjoiICAgIH1cbiAgfVxuXG4gIEZ1dHVyZTx2b2lkPiBmZXRjaFRpZGVzKHtib29sIHJldHJ5UGF1c2VkID0gZmFsc2V9KSBhc3luYyB7XG4gICAgdHJ5IHtcbiAgICAgIGZpbmFsIHJlcXVlc3RlZENhY2hlS2V5ID0gX3RpZGVDYWNoZUtleTtcblxuIn0seyJuYW1lIjoidGlkZS1jYWNoZS01Iiwib2xkIjoiICAgICAgICB9LFxuICAgICAgKTtcblxuICAgICAgZmluYWwgcmVzcG9uc2UgPSBhd2FpdCBodHRwXG4gICAgICAgICAgLmdldCh1cmkpXG4gICAgICAgICAgLnRpbWVvdXQoY29uc3QgRHVyYXRpb24oc2Vjb25kczogMzApKTtcblxuICAgICAgaWYgKHJlc3BvbnNlLnN0YXR1c0NvZGUgIT0gMjAwKSByZXR1cm47XG5cbiAgICAgIGZpbmFsIGRhdGEgPSBqc29uRGVjb2RlKHJlc3BvbnNlLmJvZHkpO1xuXG4gICAgICBpZiAoZGF0YVsnb2snXSAhPSB0cnVlIHx8XG4gICAgICAgICAgIW1vdW50ZWQgfHxcbiAgICAgICAgICByZXF1ZXN0ZWRDYWNoZUtleSAhPSBfdGlkZUNhY2hlS2V5KSB7XG4gICAgICAgIHJldHVybjtcbiAgICAgIH1cblxuICAgICAgZmluYWwgZXh0cmVtZXMgPSBfdG9MaXN0KGRhdGFbJ2V4dHJlbWVzJ10pO1xuXG4iLCJuZXciOiIgICAgICAgIH0sXG4gICAgICApO1xuXG4gICAgICBmaW5hbCByZXN1bHQgPSBhd2FpdCBfdGlkZUNsaWVudC5sb2FkKHVyaSwgY2FjaGVLZXk6IHJlcXVlc3RlZENhY2hlS2V5LCByZXRyeVBhdXNlZDogcmV0cnlQYXVzZWQpO1xuICAgICAgaWYgKCFtb3VudGVkIHx8IHJlcXVlc3RlZENhY2hlS2V5ICE9IF90aWRlQ2FjaGVLZXkpIHJldHVybjtcbiAgICAgIHNldFN0YXRlKCgpIHsgX3RpZGVOb3RpY2UgPSByZXN1bHQubm90aWNlOyB9KTtcbiAgICAgIGZpbmFsIGRhdGEgPSByZXN1bHQucGF5bG9hZDtcbiAgICAgIGlmIChkYXRhID09IG51bGwpIHJldHVybjtcblxuICAgICAgZmluYWwgZXh0cmVtZXMgPSBfdG9MaXN0KGRhdGFbJ2V4dHJlbWVzJ10pO1xuXG4ifSx7Im5hbWUiOiJ0aWRlLWNhY2hlLTYiLCJvbGQiOiIgICAgICBpZiAoIW1vdW50ZWQpIHJldHVybjtcblxuICAgICAgc2V0U3RhdGUoKCkge1xuICAgICAgICBfdGlkZXNDaGVja2VkID0gRGF0ZVRpbWUubm93KCk7XG5cbiAgICAgICAgZGFpbHlUaWRlcyA9IGdyb3VwZWQ7XG4gICAgICAgIG5leHRUaWRlVHlwZSA9IG5lYXJlc3RUeXBlO1xuIiwibmV3IjoiICAgICAgaWYgKCFtb3VudGVkKSByZXR1cm47XG5cbiAgICAgIHNldFN0YXRlKCgpIHtcbiAgICAgICAgX3RpZGVzQ2hlY2tlZCA9IHJlc3VsdC5jb3ZlcnNGb3JlY2FzdCA/IHJlc3VsdC5jaGVja2VkQXQgOiBudWxsO1xuXG4gICAgICAgIGRhaWx5VGlkZXMgPSBncm91cGVkO1xuICAgICAgICBuZXh0VGlkZVR5cGUgPSBuZWFyZXN0VHlwZTtcbiJ9LHsibmFtZSI6InRpZGUtY2FjaGUtNyIsIm9sZCI6IiAgICAgICAgICAgIGRhdGFbJ2RhdHVtJ10/LnRvU3RyaW5nKCkgPz8gJyc7XG4gICAgICB9KTtcblxuICAgICAgdHJ5IHtcbiAgICAgICAgZmluYWwgcHJlZnMgPVxuICAgICAgICBhd2FpdCBTaGFyZWRQcmVmZXJlbmNlcy5nZXRJbnN0YW5jZSgpO1xuXG4gICAgICAgIGF3YWl0IHByZWZzLnNldFN0cmluZyhcbiAgICAgICAgICByZXF1ZXN0ZWRDYWNoZUtleSxcbiAgICAgICAgICByZXNwb25zZS5ib2R5LFxuICAgICAgICApO1xuXG4gICAgICAgIGF3YWl0IHByZWZzLnNldEludChcbiAgICAgICAgICAnJHtyZXF1ZXN0ZWRDYWNoZUtleX1fc2F2ZWRfYXQnLFxuICAgICAgICAgIERhdGVUaW1lLm5vdygpLm1pbGxpc2Vjb25kc1NpbmNlRXBvY2gsXG4gICAgICAgICk7XG4gICAgICB9IGNhdGNoIChlKSB7XG4gICAgICAgIGRlYnVnUHJpbnQoJ1RpZGUgY2FjaGUgd3JpdGUgZXJyb3I6ICRlJyk7XG4gICAgICB9XG4gICAgfSBjYXRjaCAoZSkge1xuICAgICAgZGVidWdQcmludCgnVGlkZSBmZXRjaCBlcnJvcjogJGUnKTtcbiAgICB9XG4iLCJuZXciOiIgICAgICAgICAgICBkYXRhWydkYXR1bSddPy50b1N0cmluZygpID8/ICcnO1xuICAgICAgfSk7XG5cbiAgICB9IGNhdGNoIChlKSB7XG4gICAgICBkZWJ1Z1ByaW50KCdUaWRlIGZldGNoIGVycm9yOiAkZScpO1xuICAgIH1cbiJ9LHsibmFtZSI6InRpZGUtY2FjaGUtOCIsIm9sZCI6IiAgICAgIHN1bnJpc2VUaW1lID0gJy0tJztcbiAgICAgIHN1bnNldFRpbWUgPSAnLS0nO1xuICAgICAgdGlkZURhdHVtID0gJyc7XG5cbiAgICAgIGZvcmVjYXN0RGF0ZXMgPSBbXTtcbiAgICAgIGZvcmVjYXN0V2luZFNwZWVkcyA9IFtdO1xuIiwibmV3IjoiICAgICAgc3VucmlzZVRpbWUgPSAnLS0nO1xuICAgICAgc3Vuc2V0VGltZSA9ICctLSc7XG4gICAgICB0aWRlRGF0dW0gPSAnJztcbiAgICAgIF90aWRlTm90aWNlID0gbnVsbDtcblxuICAgICAgZm9yZWNhc3REYXRlcyA9IFtdO1xuICAgICAgZm9yZWNhc3RXaW5kU3BlZWRzID0gW107XG4ifSx7Im5hbWUiOiJ0aWRlLWNhY2hlLTkiLCJvbGQiOiIgICAgICAgICksXG4gICAgICAgIGNvbnN0IFNpemVkQm94KGhlaWdodDogNSksXG4gICAgICAgIGlmIChldmVudHMuaXNFbXB0eSlcbiAgICAgICAgICBjb25zdCBUZXh0KFxuICAgICAgICAgICAgJ05vIHRpZGUgZGF0YScsXG4gICAgICAgICAgICBzdHlsZTogVGV4dFN0eWxlKFxuICAgICAgICAgICAgICBmb250U2l6ZTogMTIsXG4gICAgICAgICAgICAgIGNvbG9yOiBDb2xvcnMuYmx1ZUdyZXksXG4iLCJuZXciOiIgICAgICAgICksXG4gICAgICAgIGNvbnN0IFNpemVkQm94KGhlaWdodDogNSksXG4gICAgICAgIGlmIChldmVudHMuaXNFbXB0eSlcbiAgICAgICAgICBUZXh0KFxuICAgICAgICAgICAgX3RpZGVOb3RpY2UgPz8gJ05vIHRpZGUgZGF0YScsXG4gICAgICAgICAgICBzdHlsZTogVGV4dFN0eWxlKFxuICAgICAgICAgICAgICBmb250U2l6ZTogMTIsXG4gICAgICAgICAgICAgIGNvbG9yOiBDb2xvcnMuYmx1ZUdyZXksXG4ifV19LHsicGF0aCI6ImxpYi90aWRlX3ByZWRpY3Rpb25zLmRhcnQiLCJiYWNrdXBfbmFtZSI6InRpZGVfcHJlZGljdGlvbnMuZGFydC5iYWsiLCJwYXlsb2FkIjoiYVcxd2IzSjBJQ2RrWVhKME9tRnplVzVqSnpzS2FXMXdiM0owSUNka1lYSjBPbU52Ym5abGNuUW5Pd3BwYlhCdmNuUWdKMlJoY25RNmJXRjBhQ2M3Q2dwcGJYQnZjblFnSjNCaFkydGhaMlU2YUhSMGNDOW9kSFJ3TG1SaGNuUW5JR0Z6SUdoMGRIQTdDbWx0Y0c5eWRDQW5jR0ZqYTJGblpUcHphR0Z5WldSZmNISmxabVZ5Wlc1alpYTXZjMmhoY21Wa1gzQnlaV1psY21WdVkyVnpMbVJoY25Rbk93b0tSR0YwWlZScGJXVWdYM1JwWkdWRVlYa29SR0YwWlZScGJXVWdkbUZzZFdVcElIc0tJQ0JtYVc1aGJDQnNiMk5oYkNBOUlIWmhiSFZsTG5SdlZYUmpLQ2t1YzNWaWRISmhZM1FvWTI5dWMzUWdSSFZ5WVhScGIyNG9hRzkxY25NNklEUXBLVHNLSUNCeVpYUjFjbTRnUkdGMFpWUnBiV1V1ZFhSaktHeHZZMkZzTG5sbFlYSXNJR3h2WTJGc0xtMXZiblJvTENCc2IyTmhiQzVrWVhrc0lEUXBPd3A5Q2dwaWIyOXNJSE5vYjNWc1pFTm9aV05yVkdsa1pYTW9ld29nSUhKbGNYVnBjbVZrSUVSaGRHVlVhVzFsSUc1dmR5d0tJQ0J5WlhGMWFYSmxaQ0JFWVhSbFZHbHRaVDhnWTJobFkydGxaRUYwTEFvZ0lISmxjWFZwY21Wa0lFUmhkR1ZVYVcxbFB5QmhkSFJsYlhCMFpXUkJkQ3dLZlNrZ2V3b2dJR2xtSUNoamFHVmphMlZrUVhRZ0lUMGdiblZzYkNBbUppQmZkR2xrWlVSaGVTaGphR1ZqYTJWa1FYUXBJRDA5SUY5MGFXUmxSR0Y1S0c1dmR5a3BJSHNLSUNBZ0lISmxkSFZ5YmlCbVlXeHpaVHNLSUNCOUNpQWdjbVYwZFhKdUlHRjBkR1Z0Y0hSbFpFRjBJRDA5SUc1MWJHd2dmSHdLSUNBZ0lDQWdibTkzTG1ScFptWmxjbVZ1WTJVb1lYUjBaVzF3ZEdWa1FYUXBJRDQ5SUdOdmJuTjBJRVIxY21GMGFXOXVLRzFwYm5WMFpYTTZJREV3S1RzS2ZRb0tZMnhoYzNNZ1ZHbGtaVkJ5WldScFkzUnBiMjVTWlhOMWJIUWdld29nSUdOdmJuTjBJRlJwWkdWUWNtVmthV04wYVc5dVVtVnpkV3gwS0FvZ0lDQWdJQ0IwYUdsekxuQmhlV3h2WVdRc0lIUm9hWE11WTI5MlpYSnpSbTl5WldOaGMzUXNJSFJvYVhNdWJtOTBhV05sTENCMGFHbHpMbU5vWldOclpXUkJkQ2s3Q2lBZ1ptbHVZV3dnVFdGd1BGTjBjbWx1Wnl3Z1pIbHVZVzFwWXo0L0lIQmhlV3h2WVdRN0NpQWdabWx1WVd3Z1ltOXZiQ0JqYjNabGNuTkdiM0psWTJGemREc0tJQ0JtYVc1aGJDQlRkSEpwYm1jL0lHNXZkR2xqWlRzS0lDQm1hVzVoYkNCRVlYUmxWR2x0WlNCamFHVmphMlZrUVhRN0NuMEtDbU5zWVhOeklGUnBaR1ZRY21Wa2FXTjBhVzl1UTJ4cFpXNTBJSHNLSUNCVWFXUmxVSEpsWkdsamRHbHZia05zYVdWdWRDaDdDaUFnSUNCb2RIUndMa05zYVdWdWREOGdZMnhwWlc1MExBb2dJQ0FnUm5WMGRYSmxQRk5vWVhKbFpGQnlaV1psY21WdVkyVnpQaUJHZFc1amRHbHZiaWdwUHlCd2NtVm1aWEpsYm1ObGN5d0tJQ0FnSUVSaGRHVlVhVzFsSUVaMWJtTjBhVzl1S0NrL0lHTnNiMk5yTEFvZ0lDQWdVM1J5YVc1bklFWjFibU4wYVc5dUtDay9JR055WldGMFpVbGtMQW9nSUgwcElDQTZJRjlqYkdsbGJuUWdQU0JqYkdsbGJuUXNDaUFnSUNBZ0lDQWdYM0J5WldabGNtVnVZMlZ6SUQwZ2NISmxabVZ5Wlc1alpYTWdQejhnVTJoaGNtVmtVSEpsWm1WeVpXNWpaWE11WjJWMFNXNXpkR0Z1WTJVc0NpQWdJQ0FnSUNBZ1gyTnNiMk5ySUQwZ1kyeHZZMnNnUHo4Z1JHRjBaVlJwYldVdWJtOTNMQW9nSUNBZ0lDQWdJRjlqY21WaGRHVkpaQ0E5SUdOeVpXRjBaVWxrSUQ4L0lGOXlZVzVrYjIxSlpEc0tDaUFnYzNSaGRHbGpJR052Ym5OMElGOXBaR1Z1ZEdsMGVVdGxlU0E5SUNkelpXRndiMmx1ZEY5MGFXUmxYMmx1YzNSaGJHeGhkR2x2Ymw5Mk1TYzdDaUFnYzNSaGRHbGpJR052Ym5OMElGOWpjbVZrYVhSUVlYVnpaVXRsZVNBOUlDZHpaV0Z3YjJsdWRGOTBhV1JsWDNCeWIzWnBaR1Z5WDNKbGRISjVYMkYwWDNZeUp6c0tJQ0J6ZEdGMGFXTWdZMjl1YzNRZ2RXNWhkbUZwYkdGaWJHVk9iM1JwWTJVZ1BTQW5WR2xrWlNCMWNHUmhkR1Z6SUhSbGJYQnZjbUZ5YVd4NUlIVnVZWFpoYVd4aFlteGxKenNLSUNCbWFXNWhiQ0JvZEhSd0xrTnNhV1Z1ZEQ4Z1gyTnNhV1Z1ZERzS0lDQm1hVzVoYkNCR2RYUjFjbVU4VTJoaGNtVmtVSEpsWm1WeVpXNWpaWE0rSUVaMWJtTjBhVzl1S0NrZ1gzQnlaV1psY21WdVkyVnpPd29nSUdacGJtRnNJRVJoZEdWVWFXMWxJRVoxYm1OMGFXOXVLQ2tnWDJOc2IyTnJPd29nSUdacGJtRnNJRk4wY21sdVp5QkdkVzVqZEdsdmJpZ3BJRjlqY21WaGRHVkpaRHNLSUNCbWFXNWhiQ0JmYVc1bWJHbG5hSFFnUFNBOFUzUnlhVzVuTENCR2RYUjFjbVU4Vkdsa1pWQnlaV1JwWTNScGIyNVNaWE4xYkhRK1BudDlPd29nSUVaMWRIVnlaVHhUZEhKcGJtYytQeUJmYVdSbGJuUnBkSGs3Q2dvZ0lITjBZWFJwWXlCVGRISnBibWNnWDNKaGJtUnZiVWxrS0NrZ2V3b2dJQ0FnWm1sdVlXd2djbUZ1Wkc5dElEMGdVbUZ1Wkc5dExuTmxZM1Z5WlNncE93b2dJQ0FnY21WMGRYSnVJRXhwYzNRdVoyVnVaWEpoZEdVb0NpQWdJQ0FnSUNBZ0lDQWdJREUyTENBb1h5a2dQVDRnY21GdVpHOXRMbTVsZUhSSmJuUW9NalUyS1M1MGIxSmhaR2w0VTNSeWFXNW5LREUyS1M1d1lXUk1aV1owS0RJc0lDY3dKeWtwQ2lBZ0lDQWdJQ0FnTG1wdmFXNG9LVHNLSUNCOUNnb2dJRVoxZEhWeVpUeFRkSEpwYm1jK0lGOXBibk4wWVd4c1lYUnBiMjRvVTJoaGNtVmtVSEpsWm1WeVpXNWpaWE1nY0hKbFpuTXBJRDArQ2lBZ0lDQWdJRjlwWkdWdWRHbDBlU0EvUHowZ0tDZ3BJR0Z6ZVc1aklIc0tJQ0FnSUNBZ0lDQjJZWElnZG1Gc2RXVWdQU0J3Y21WbWN5NW5aWFJUZEhKcGJtY29YMmxrWlc1MGFYUjVTMlY1S1RzS0lDQWdJQ0FnSUNCcFppQW9kbUZzZFdVZ1BUMGdiblZzYkNCOGZDQWhVbVZuUlhod0tISW5YbHRoTFdZd0xUbGRlek15ZlNRbktTNW9ZWE5OWVhSamFDaDJZV3gxWlNrcElIc0tJQ0FnSUNBZ0lDQWdJSFpoYkhWbElEMGdYMk55WldGMFpVbGtLQ2s3Q2lBZ0lDQWdJQ0FnSUNCcFppQW9JVkpsWjBWNGNDaHlKMTViWVMxbU1DMDVYWHN6TW4wa0p5a3VhR0Z6VFdGMFkyZ29kbUZzZFdVcEtTQjdDaUFnSUNBZ0lDQWdJQ0FnSUhSb2NtOTNJR052Ym5OMElFWnZjbTFoZEVWNFkyVndkR2x2YmlnblNXNTJZV3hwWkNCMGFXUmxJR2x1YzNSaGJHeGhkR2x2YmlCcFpHVnVkR2xtYVdWeUp5azdDaUFnSUNBZ0lDQWdJQ0I5Q2lBZ0lDQWdJQ0FnSUNCcFppQW9JV0YzWVdsMElIQnlaV1p6TG5ObGRGTjBjbWx1WnloZmFXUmxiblJwZEhsTFpYa3NJSFpoYkhWbEtTa2dld29nSUNBZ0lDQWdJQ0FnSUNCMGFISnZkeUJUZEdGMFpVVnljbTl5S0NkRGIzVnNaQ0J1YjNRZ2NtVjBZV2x1SUhScFpHVWdhVzV6ZEdGc2JHRjBhVzl1SUdsa1pXNTBhV1pwWlhJbktUc0tJQ0FnSUNBZ0lDQWdJSDBLSUNBZ0lDQWdJQ0I5Q2lBZ0lDQWdJQ0FnY21WMGRYSnVJSFpoYkhWbE93b2dJQ0FnSUNCOUtTZ3BPd29LSUNCR2RYUjFjbVU4Vkdsa1pWQnlaV1JwWTNScGIyNVNaWE4xYkhRK0lHeHZZV1FvVlhKcElIVnlhU3dLSUNBZ0lDQWdlM0psY1hWcGNtVmtJRk4wY21sdVp5QmpZV05vWlV0bGVTd2dZbTl2YkNCeVpYUnllVkJoZFhObFpDQTlJR1poYkhObGZTa2dld29nSUNBZ1ptbHVZV3dnWTNWeWNtVnVkQ0E5SUY5cGJtWnNhV2RvZEZ0allXTm9aVXRsZVYwN0NpQWdJQ0JwWmlBb1kzVnljbVZ1ZENBaFBTQnVkV3hzS1NCeVpYUjFjbTRnWTNWeWNtVnVkRHNLSUNBZ0lHWnBibUZzSUhKbGNYVmxjM1FnUFNCZmJHOWhaQ2gxY21rc0lHTmhZMmhsUzJWNUxDQnlaWFJ5ZVZCaGRYTmxaQ2s3Q2lBZ0lDQmZhVzVtYkdsbmFIUmJZMkZqYUdWTFpYbGRJRDBnY21WeGRXVnpkRHNLSUNBZ0lISmxkSFZ5YmlCeVpYRjFaWE4wTG5kb1pXNURiMjF3YkdWMFpTZ29LU0E5UGlCZmFXNW1iR2xuYUhRdWNtVnRiM1psS0dOaFkyaGxTMlY1S1NrN0NpQWdmUW9LSUNCaWIyOXNJRjlqYjNabGNuTW9UV0Z3UEZOMGNtbHVaeXdnWkhsdVlXMXBZejQvSUhCaGVXeHZZV1FzSUVSaGRHVlVhVzFsSUc1dmR5a2dld29nSUNBZ2FXWWdLSEJoZVd4dllXUWdQVDBnYm5Wc2JDa2djbVYwZFhKdUlHWmhiSE5sT3dvZ0lDQWdabWx1WVd3Z2MzUmhjblFnUFNCd1lYbHNiMkZrV3lkamIzWmxjbUZuWlY5emRHRnlkQ2RkT3dvZ0lDQWdabWx1WVd3Z1pXNWtJRDBnY0dGNWJHOWhaRnNuWTI5MlpYSmhaMlZmWlc1a0oxMDdDaUFnSUNCbWFXNWhiQ0JrWVhrZ1BTQmZkR2xrWlVSaGVTaHViM2NwTG0xcGJHeHBjMlZqYjI1a2MxTnBibU5sUlhCdlkyZ2dmaThnTVRBd01Ec0tJQ0FnSUhKbGRIVnliaUJ6ZEdGeWRDQnBjeUJ1ZFcwZ0ppWWdaVzVrSUdseklHNTFiU0FtSmlCemRHRnlkQ0E4UFNCa1lYa2dKaVlnWlc1a0lENDlJR1JoZVNBcklEY2dLaUE0TmpRd01Ec0tJQ0I5Q2dvZ0lFMWhjRHhUZEhKcGJtY3NJR1I1Ym1GdGFXTStQeUJmWTJGamFHVmtLQW9nSUNBZ0lDQlRhR0Z5WldSUWNtVm1aWEpsYm1ObGN5QndjbVZtY3l3Z1UzUnlhVzVuSUd0bGVTd2dSR0YwWlZScGJXVWdibTkzS1NCN0NpQWdJQ0JtYVc1aGJDQnlZWGNnUFNCd2NtVm1jeTVuWlhSVGRISnBibWNvYTJWNUtUc0tJQ0FnSUdacGJtRnNJSE5oZG1Wa0lEMGdjSEpsWm5NdVoyVjBTVzUwS0Nja2UydGxlWDFmYzJGMlpXUmZZWFFuS1RzS0lDQWdJR2xtSUNoeVlYY2dQVDBnYm5Wc2JDQjhmQ0J6WVhabFpDQTlQU0J1ZFd4c0lIeDhJSE5oZG1Wa0lENGdibTkzTG0xcGJHeHBjMlZqYjI1a2MxTnBibU5sUlhCdlkyZ3BJSHNLSUNBZ0lDQWdjbVYwZFhKdUlHNTFiR3c3Q2lBZ0lDQjlDaUFnSUNCMGNua2dld29nSUNBZ0lDQm1hVzVoYkNCa1lYUmhJRDBnYW5OdmJrUmxZMjlrWlNoeVlYY3BPd29nSUNBZ0lDQnBaaUFvWkdGMFlTQnBjeUVnVFdGd1BGTjBjbWx1Wnl3Z1pIbHVZVzFwWXo0Z2ZId0tJQ0FnSUNBZ0lDQWdJR1JoZEdGYkoyOXJKMTBnSVQwZ2RISjFaU0I4ZkFvZ0lDQWdJQ0FnSUNBZ1pHRjBZVnNuWlhoMGNtVnRaWE1uWFNCcGN5RWdUR2x6ZENrZ2V3b2dJQ0FnSUNBZ0lISmxkSFZ5YmlCdWRXeHNPd29nSUNBZ0lDQjlDaUFnSUNBZ0lDOHZJRTFwWjNKaGRHVWdkR2hsSUdWNGFYTjBhVzVuSUhCb2IyNWxJR05oWTJobElIVnphVzVuSUhSb1pTQnZjbWxuYVc1aGJDQnlaWFJ5YVdWMllXd2dkR2x0WlM0S0lDQWdJQ0FnTHk4Z1VtVXRjbVZoWkdsdVp5QmhJSE5oZG1Wa0lIQnlaV1JwWTNScGIyNGdiWFZ6ZENCdVpYWmxjaUJsZUhSbGJtUWdhWFJ6SUdSaGRHVWdZMjkyWlhKaFoyVXVDaUFnSUNBZ0lHWnBibUZzSUdSaGVTQTlJRjkwYVdSbFJHRjVLRVJoZEdWVWFXMWxMbVp5YjIxTmFXeHNhWE5sWTI5dVpITlRhVzVqWlVWd2IyTm9LSE5oZG1Wa0tTazdDaUFnSUNBZ0lHUmhkR0ZiSjJOdmRtVnlZV2RsWDNOMFlYSjBKMTBnUHo4OUlHUmhlUzV0YVd4c2FYTmxZMjl1WkhOVGFXNWpaVVZ3YjJOb0lINHZJREV3TURBN0NpQWdJQ0FnSUdSaGRHRmJKMk52ZG1WeVlXZGxYMlZ1WkNkZElEOC9QUW9nSUNBZ0lDQWdJQ0FnWkdGNUxtRmtaQ2hqYjI1emRDQkVkWEpoZEdsdmJpaGtZWGx6T2lBM0tTa3ViV2xzYkdselpXTnZibVJ6VTJsdVkyVkZjRzlqYUNCK0x5QXhNREF3T3dvZ0lDQWdJQ0JrWVhSaFd5ZG1aWFJqYUdWa1gyRjBKMTBnUHo4OUlITmhkbVZrSUg0dklERXdNREE3Q2lBZ0lDQWdJR1pwYm1Gc0lHVnVaQ0E5SUdSaGRHRmJKMk52ZG1WeVlXZGxYMlZ1WkNkZE93b2dJQ0FnSUNCeVpYUjFjbTRnWlc1a0lHbHpJRzUxYlNBbUppQmxibVFnUGlCdWIzY3ViV2xzYkdselpXTnZibVJ6VTJsdVkyVkZjRzlqYUNCK0x5QXhNREF3Q2lBZ0lDQWdJQ0FnSUNBL0lHUmhkR0VLSUNBZ0lDQWdJQ0FnSURvZ2JuVnNiRHNLSUNBZ0lIMGdiMjRnUm05eWJXRjBSWGhqWlhCMGFXOXVJSHNLSUNBZ0lDQWdjbVYwZFhKdUlHNTFiR3c3Q2lBZ0lDQjlDaUFnZlFvS0lDQkdkWFIxY21VOFZHbGtaVkJ5WldScFkzUnBiMjVTWlhOMWJIUStJRjlzYjJGa0tBb2dJQ0FnSUNCVmNta2dkWEpwTENCVGRISnBibWNnYTJWNUxDQmliMjlzSUhKbGRISjVVR0YxYzJWa0tTQmhjM2x1WXlCN0NpQWdJQ0JtYVc1aGJDQndjbVZtY3lBOUlHRjNZV2wwSUY5d2NtVm1aWEpsYm1ObGN5Z3BPd29nSUNBZ1ptbHVZV3dnYm05M0lEMGdYMk5zYjJOcktDazdDaUFnSUNCbWFXNWhiQ0J6WldOdmJtUnpJRDBnYm05M0xtMXBiR3hwYzJWamIyNWtjMU5wYm1ObFJYQnZZMmdnZmk4Z01UQXdNRHNLSUNBZ0lHWnBibUZzSUhOaGRtVmtJRDBnWDJOaFkyaGxaQ2h3Y21WbWN5d2dhMlY1TENCdWIzY3BPd29nSUNBZ2FXWWdLRjlqYjNabGNuTW9jMkYyWldRc0lHNXZkeWtwSUhzS0lDQWdJQ0FnY21WMGRYSnVJRlJwWkdWUWNtVmthV04wYVc5dVVtVnpkV3gwS0hOaGRtVmtMQ0IwY25WbExDQnVkV3hzTENCdWIzY3BPd29nSUNBZ2ZRb2dJQ0FnWm1sdVlXd2daMnh2WW1Gc1VHRjFjMlVnUFNCd2NtVm1jeTVuWlhSSmJuUW9YMk55WldScGRGQmhkWE5sUzJWNUtTQS9QeUF3T3dvZ0lDQWdabWx1WVd3Z2JHOWpZWFJwYjI1UVlYVnpaU0E5SUhCeVpXWnpMbWRsZEVsdWRDZ25KSHRyWlhsOVgzSmxkSEo1WDJGMFgzWXlKeWtnUHo4Z01Ec0tJQ0FnSUdsbUlDZ2hjbVYwY25sUVlYVnpaV1FnSmlZZ0tHZHNiMkpoYkZCaGRYTmxJRDRnYzJWamIyNWtjeUI4ZkNCc2IyTmhkR2x2YmxCaGRYTmxJRDRnYzJWamIyNWtjeWtwSUhzS0lDQWdJQ0FnY21WMGRYSnVJRlJwWkdWUWNtVmthV04wYVc5dVVtVnpkV3gwS0hOaGRtVmtMQ0JtWVd4elpTd2dkVzVoZG1GcGJHRmliR1ZPYjNScFkyVXNJRzV2ZHlrN0NpQWdJQ0I5Q2lBZ0lDQm1hVzVoYkNCamIyNXVaV04wYVc5dUlEMGdYMk5zYVdWdWRDQS9QeUJvZEhSd0xrTnNhV1Z1ZENncE93b2dJQ0FnZEhKNUlIc0tJQ0FnSUNBZ1ptbHVZV3dnYVdSbGJuUnBkSGtnUFNCaGQyRnBkQ0JmYVc1emRHRnNiR0YwYVc5dUtIQnlaV1p6S1RzS0lDQWdJQ0FnWm1sdVlXd2djbVZ6Y0c5dWMyVWdQU0JoZDJGcGRDQmpiMjV1WldOMGFXOXVMbWRsZENoMWNta3NJR2hsWVdSbGNuTTZJSHNLSUNBZ0lDQWdJQ0FuV0MxVFpXRlFiMmx1ZEMxVWFXUmxMVU5zYVdWdWRDYzZJR2xrWlc1MGFYUjVMQW9nSUNBZ0lDQWdJR2xtSUNoeVpYUnllVkJoZFhObFpDa2dKMWd0VTJWaFVHOXBiblF0Vkdsa1pTMVFjbTlpWlNjNklDY3hKeXdLSUNBZ0lDQWdmU2t1ZEdsdFpXOTFkQ2hqYjI1emRDQkVkWEpoZEdsdmJpaHpaV052Ym1Sek9pQXpNQ2twT3dvZ0lDQWdJQ0JtYVc1aGJDQmtlVzVoYldsaklHUmxZMjlrWldRZ1BTQnFjMjl1UkdWamIyUmxLSEpsYzNCdmJuTmxMbUp2WkhrcE93b2dJQ0FnSUNCbWFXNWhiQ0JrWVhSaElEMEtJQ0FnSUNBZ0lDQWdJR1JsWTI5a1pXUWdhWE1nVFdGd1BGTjBjbWx1Wnl3Z1pIbHVZVzFwWXo0Z1B5QmtaV052WkdWa0lEb2dQRk4wY21sdVp5d2daSGx1WVcxcFl6NTdmVHNLSUNBZ0lDQWdabWx1WVd3Z2NtVjBjbmtnUFNCa1lYUmhXeWR5WlhSeWVWOWhkQ2RkT3dvZ0lDQWdJQ0JtYVc1aGJDQnlaWFJ5ZVVGMElEMGdjbVYwY25rZ2FYTWdiblZ0Q2lBZ0lDQWdJQ0FnSUNBL0lISmxkSEo1TG5SdlNXNTBLQ2t1WTJ4aGJYQW9jMlZqYjI1a2N5QXJJRFl3TENCelpXTnZibVJ6SUNzZ09EWTBNREFwQ2lBZ0lDQWdJQ0FnSUNBNklITmxZMjl1WkhNZ0t5QTVNREE3Q2lBZ0lDQWdJR1pwYm1Gc0lISmxZWE52YmlBOUlHUmhkR0ZiSjNKbFlYTnZiaWRkT3dvZ0lDQWdJQ0JwWmlBb2NtVmhjMjl1SUQwOUlDZGpjbVZrYVhSelgyVjRhR0YxYzNSbFpDY2dmSHdLSUNBZ0lDQWdJQ0FnSUhKbFlYTnZiaUE5UFNBblkzSmxaR1Z1ZEdsaGJITmZkVzVoZG1GcGJHRmliR1VuS1NCN0NpQWdJQ0FnSUNBZ1lYZGhhWFFnY0hKbFpuTXVjMlYwU1c1MEtGOWpjbVZrYVhSUVlYVnpaVXRsZVN3Z2NtVjBjbmxCZENrN0NpQWdJQ0FnSUgwS0lDQWdJQ0FnYVdZZ0tISmxjM0J2Ym5ObExuTjBZWFIxYzBOdlpHVWdJVDBnTWpBd0lIeDhDaUFnSUNBZ0lDQWdJQ0JrWVhSaFd5ZHZheWRkSUNFOUlIUnlkV1VnZkh3S0lDQWdJQ0FnSUNBZ0lHUmhkR0ZiSjJWNGRISmxiV1Z6SjEwZ2FYTWhJRXhwYzNRcElIc0tJQ0FnSUNBZ0lDQmhkMkZwZENCd2NtVm1jeTV6WlhSSmJuUW9KeVI3YTJWNWZWOXlaWFJ5ZVY5aGRGOTJNaWNzSUhKbGRISjVRWFFwT3dvZ0lDQWdJQ0FnSUhKbGRIVnliaUJVYVdSbFVISmxaR2xqZEdsdmJsSmxjM1ZzZENoellYWmxaQ3dnWm1Gc2MyVXNJSFZ1WVhaaGFXeGhZbXhsVG05MGFXTmxMQ0JmWTJ4dlkyc29LU2s3Q2lBZ0lDQWdJSDBLSUNBZ0lDQWdhV1lnS0hKbFlYTnZiaUFoUFNBblkzSmxaR2wwYzE5bGVHaGhkWE4wWldRbklDWW1DaUFnSUNBZ0lDQWdJQ0J5WldGemIyNGdJVDBnSjJOeVpXUmxiblJwWVd4elgzVnVZWFpoYVd4aFlteGxKeWtnZXdvZ0lDQWdJQ0FnSUdGM1lXbDBJSEJ5WldaekxuSmxiVzkyWlNoZlkzSmxaR2wwVUdGMWMyVkxaWGtwT3dvZ0lDQWdJQ0I5Q2lBZ0lDQWdJR1pwYm1Gc0lITjBZWEowSUQwZ1pHRjBZVnNuWTI5MlpYSmhaMlZmYzNSaGNuUW5YVHNLSUNBZ0lDQWdabWx1WVd3Z1pXNWtJRDBnWkdGMFlWc25ZMjkyWlhKaFoyVmZaVzVrSjEwN0NpQWdJQ0FnSUdacGJtRnNJR1psZEdOb1pXUWdQU0JrWVhSaFd5ZG1aWFJqYUdWa1gyRjBKMTA3Q2lBZ0lDQWdJR2xtSUNoemRHRnlkQ0JwY3lFZ2JuVnRJSHg4Q2lBZ0lDQWdJQ0FnSUNCbGJtUWdhWE1oSUc1MWJTQjhmQW9nSUNBZ0lDQWdJQ0FnWm1WMFkyaGxaQ0JwY3lFZ2JuVnRJSHg4Q2lBZ0lDQWdJQ0FnSUNCbGJtUWdQRDBnYzNSaGNuUWdmSHdLSUNBZ0lDQWdJQ0FnSUdWdVpDQXRJSE4wWVhKMElENGdPQ0FxSURnMk5EQXdJSHg4Q2lBZ0lDQWdJQ0FnSUNCbVpYUmphR1ZrSUQ0Z2MyVmpiMjVrY3lBcklEWXdLU0I3Q2lBZ0lDQWdJQ0FnZEdoeWIzY2dZMjl1YzNRZ1JtOXliV0YwUlhoalpYQjBhVzl1S0NkSmJuWmhiR2xrSUhScFpHVWdZMjkyWlhKaFoyVW5LVHNLSUNBZ0lDQWdmUW9nSUNBZ0lDQm1hVzVoYkNCeVpXTmxhWFpsWkVGMElEMGdYMk5zYjJOcktDazdDaUFnSUNBZ0lHWnBibUZzSUdOdmJYQnNaWFJsSUQwZ1gyTnZkbVZ5Y3loa1lYUmhMQ0J5WldObGFYWmxaRUYwS1RzS0lDQWdJQ0FnYVdZZ0tDRmpiMjF3YkdWMFpTa2dld29nSUNBZ0lDQWdJR0YzWVdsMElIQnlaV1p6TG5ObGRFbHVkQ2duSkh0clpYbDlYM0psZEhKNVgyRjBYM1l5Snl3Z2NtVjBjbmxCZENrN0NpQWdJQ0FnSUgwS0lDQWdJQ0FnWVhkaGFYUWdjSEpsWm5NdWMyVjBVM1J5YVc1bktHdGxlU3dnYW5OdmJrVnVZMjlrWlNoa1lYUmhLU2s3Q2lBZ0lDQWdJR0YzWVdsMElIQnlaV1p6TG5ObGRFbHVkQ2duSkh0clpYbDlYM05oZG1Wa1gyRjBKeXdnWm1WMFkyaGxaQzUwYjBsdWRDZ3BJQ29nTVRBd01DazdDaUFnSUNBZ0lHbG1JQ2hqYjIxd2JHVjBaU2tnZXdvZ0lDQWdJQ0FnSUdGM1lXbDBJSEJ5WldaekxuSmxiVzkyWlNnbkpIdHJaWGw5WDNKbGRISjVYMkYwWDNZeUp5azdDaUFnSUNBZ0lIMEtJQ0FnSUNBZ2NtVjBkWEp1SUZScFpHVlFjbVZrYVdOMGFXOXVVbVZ6ZFd4MEtBb2dJQ0FnSUNBZ0lDQWdaR0YwWVN3Z1kyOXRjR3hsZEdVc0lHTnZiWEJzWlhSbElEOGdiblZzYkNBNklIVnVZWFpoYVd4aFlteGxUbTkwYVdObExDQnlaV05sYVhabFpFRjBLVHNLSUNBZ0lIMGdZMkYwWTJnZ0tGOHBJSHNLSUNBZ0lDQWdZWGRoYVhRZ2NISmxabk11YzJWMFNXNTBLQ2NrZTJ0bGVYMWZjbVYwY25sZllYUmZkakluTENCelpXTnZibVJ6SUNzZ09UQXdLVHNLSUNBZ0lDQWdjbVYwZFhKdUlGUnBaR1ZRY21Wa2FXTjBhVzl1VW1WemRXeDBLSE5oZG1Wa0xDQm1ZV3h6WlN3Z2RXNWhkbUZwYkdGaWJHVk9iM1JwWTJVc0lGOWpiRzlqYXlncEtUc0tJQ0FnSUgwZ1ptbHVZV3hzZVNCN0NpQWdJQ0FnSUdsbUlDaGZZMnhwWlc1MElEMDlJRzUxYkd3cElHTnZibTVsWTNScGIyNHVZMnh2YzJVb0tUc0tJQ0FnSUgwS0lDQjlDbjBLIiwic2hhMjU2IjoiYjY5YmI3YTk2ZjE3MDdkZmY3ZDc2MWU3ZTczMjBiZDM2ODJmMTE0N2M3YmU5NmIzODI3OGY0MGZjYjM4MzRlNiJ9XQ=='))
$parsedDefinitions = ConvertFrom-Json -InputObject $definitionJson
$definitions = @($parsedDefinitions)
if ($definitions.Count -ne 2) {
    throw 'The installer file list is invalid. No project files changed.'
}
foreach ($entry in $definitions) {
    if ($null -eq $entry -or $entry -is [array] -or
        $null -eq $entry.PSObject.Properties['path'] -or
        $entry.path -isnot [string] -or [string]::IsNullOrWhiteSpace($entry.path)) {
        throw 'The installer contains an invalid file path. No project files changed.'
    }
}

function Get-SeaPointHash([byte[]]$bytes) {
    $sha = [Security.Cryptography.SHA256]::Create()
    try { return ([BitConverter]::ToString($sha.ComputeHash($bytes))).Replace('-', '').ToLowerInvariant() }
    finally { $sha.Dispose() }
}

function Get-SeaPointOriginalOffset([int]$normalizedOffset, $crlfPositions) {
    $extra = 0
    foreach ($position in $crlfPositions) {
        if ($position -ge $normalizedOffset) { break }
        $extra++
    }
    return $normalizedOffset + $extra
}

function Get-SeaPointPatchedFile([byte[]]$bytes, $definition) {
    $body = $utf8.GetString($bytes)
    $bom = ''
    while ($body.Length -gt 0 -and $body[0] -eq [char]0xFEFF) {
        $bom += [char]0xFEFF
        $body = $body.Substring(1)
    }
    $normalized = $body.Replace("`r`n", "`n").Replace("`r", "`n")
    foreach ($marker in $definition.markers) {
        if ([regex]::Matches($normalized, [regex]::Escape([string]$marker)).Count -ne 1) {
            throw ($definition.path + ' is not the expected SeaPoint file. No files changed.')
        }
    }

    # Inspect every block before making any replacements. Some old blocks are a
    # prefix of the new block; a complete new match consumes only those old
    # matches inside it. A separate old copy or any duplicate remains invalid.
    $ranges = @()
    $resolvedRanges = @()
    foreach ($patch in $definition.patches) {
        if ([string]::IsNullOrEmpty($patch.old) -or [string]::IsNullOrEmpty($patch.new) -or $patch.old -eq $patch.new) {
            throw 'The tide cache patch definition is invalid. No files changed.'
        }
        $oldMatches = [regex]::Matches($normalized, [regex]::Escape([string]$patch.old))
        $newMatches = [regex]::Matches($normalized, [regex]::Escape([string]$patch.new))
        $outsideOld = @()
        foreach ($oldMatch in $oldMatches) {
            $consumed = $false
            foreach ($newMatch in $newMatches) {
                if ($oldMatch.Index -ge $newMatch.Index -and
                    $oldMatch.Index + $oldMatch.Length -le $newMatch.Index + $newMatch.Length) {
                    $consumed = $true
                    break
                }
            }
            if (!$consumed) { $outsideOld += $oldMatch }
        }
        if ($outsideOld.Count -eq 1 -and $newMatches.Count -eq 0) {
            $match = $outsideOld[0]
            $ranges += [PSCustomObject]@{ Start = $match.Index; Length = $match.Length; New = [string]$patch.new; Name = [string]$patch.name }
            $resolvedRanges += [PSCustomObject]@{ Start = $match.Index; Length = $match.Length }
        } elseif ($outsideOld.Count -eq 0 -and $newMatches.Count -eq 1) {
            $resolvedRanges += [PSCustomObject]@{ Start = $newMatches[0].Index; Length = $newMatches[0].Length }
        } else {
            throw ($definition.path + ' contains a missing or ambiguous update block: ' + $patch.name + '. No files changed.')
        }
    }
    $previousEnd = -1
    foreach ($range in @($resolvedRanges | Sort-Object Start)) {
        if ($range.Start -lt $previousEnd) { throw ($definition.path + ' update blocks overlap. No files changed.') }
        $previousEnd = $range.Start + $range.Length
    }
    if ($ranges.Count -eq 0) { return ,$bytes }

    # Map normalized offsets back to the original bytes. Only patch spans are
    # rewritten; unpatched text, BOM and mixed line endings remain untouched.
    $crlfPositions = New-Object 'System.Collections.Generic.List[int]'
    foreach ($newline in [regex]::Matches($body, "`r`n")) {
        $crlfPositions.Add($newline.Index - $crlfPositions.Count)
    }
    $defaultNewLine = [regex]::Match($body, "`r`n|`n|`r").Value
    if ($defaultNewLine.Length -eq 0) { $defaultNewLine = "`n" }
    foreach ($range in @($ranges | Sort-Object Start -Descending)) {
        $start = Get-SeaPointOriginalOffset $range.Start $crlfPositions
        $end = Get-SeaPointOriginalOffset ($range.Start + $range.Length) $crlfPositions
        $originalBlock = $body.Substring($start, $end - $start)
        $newLine = [regex]::Match($originalBlock, "`r`n|`n|`r").Value
        if ($newLine.Length -eq 0) { $newLine = $defaultNewLine }
        $replacement = $range.New.Replace("`n", $newLine)
        $body = $body.Substring(0, $start) + $replacement + $body.Substring($end)
    }
    return ,($utf8.GetBytes($bom + $body))
}

$projectRoot = (Get-Location).ProviderPath
if (!(Test-Path -LiteralPath (Join-Path $projectRoot 'pubspec.yaml') -PathType Leaf)) {
    throw 'Run this from the SeaPoint project folder in the Android Studio Terminal. No files changed.'
}
# Check the deployed cache API without making a WorldTides request.
Write-Host 'Checking SeaPoint tide caching. A sleeping server may take a moment to wake.'
[Net.ServicePointManager]::SecurityProtocol = [Net.ServicePointManager]::SecurityProtocol -bor [Net.SecurityProtocolType]::Tls12
$cloudReady = $false
$cloudClock = [Diagnostics.Stopwatch]::StartNew()
for ($attempt = 0; $attempt -lt 10; $attempt++) {
    $remaining = 90 - [int]$cloudClock.Elapsed.TotalSeconds
    if ($remaining -le 0) { break }
    try {
        $health = Invoke-RestMethod -Uri 'https://seapoint-backend.onrender.com/tides/status' -TimeoutSec ([Math]::Min(60, $remaining))
        if ($health.service_version -eq 'tide-cache-v2' -and
            $health.configured -eq $true -and
            $health.status -in @('ready','paused')) {
            $cloudReady = $true
            break
        }
    } catch { }
    if ($attempt -lt 9) { Start-Sleep -Seconds 2 }
}
if (!$cloudReady) {
    throw 'The SeaPoint tide cache service is not ready. No project files changed. Please try again shortly.'
}
Write-Host 'The tide cache service is ready. Existing saved tides will be retained.'

$items = @()
foreach ($definition in $definitions) {
    $path = Join-Path $projectRoot $definition.path
    $exists = Test-Path -LiteralPath $path -PathType Leaf
    if ((Test-Path -LiteralPath $path) -and !$exists) {
        throw ($definition.path + ' is not a regular file. No files changed.')
    }
    $original = [byte[]]@()
    if ($exists) { $original = [IO.File]::ReadAllBytes($path) }
    if ($null -ne $definition.PSObject.Properties['payload']) {
        $payload = [Convert]::FromBase64String([string]$definition.payload)
        if ((Get-SeaPointHash $payload) -ne $definition.sha256) {
            throw 'An embedded trip update file failed verification. No files changed.'
        }
        if ($exists) {
            $oldText = $utf8.GetString($original).TrimStart([char]0xFEFF).Replace("`r`n", "`n")
            if ($oldText -ne $utf8.GetString($payload)) {
                throw ($definition.path + ' has other local changes. No files changed.')
            }
            $payload = $original
        }
    } else {
        if (!$exists) { throw ($definition.path + ' is missing. No files changed.') }
        if ($definition.path -eq 'pubspec.yaml' -and
            [regex]::IsMatch($utf8.GetString($original), '(?m)^  path_provider:')) {
            $payload = $original
        } else { $payload = Get-SeaPointPatchedFile $original $definition }
    }
    $items += [PSCustomObject]@{
        Exists = $exists
        Relative = [string]$definition.path
        Path = $path
        BackupName = [string]$definition.backup_name
        Original = $original
        OriginalHash = Get-SeaPointHash $original
        Payload = $payload
        PayloadHash = Get-SeaPointHash $payload
    }
}
if (@($items | Where-Object { $_.OriginalHash -ne $_.PayloadHash }).Count -eq 0) {
    Write-Host 'The SeaPoint tide cache update is already installed. Stop the app and click Run in Android Studio to load it on your phone.'

    return
}
foreach ($item in $items) {
    $existsNow = Test-Path -LiteralPath $item.Path -PathType Leaf
    if ($existsNow -ne $item.Exists -or
        ($existsNow -and (Get-SeaPointHash ([IO.File]::ReadAllBytes($item.Path))) -ne $item.OriginalHash)) {
        throw 'A SeaPoint file changed while the update was being prepared. No files changed.'
    }
}

$backupDirectory = Join-Path $projectRoot ('.seapoint-backups/tide-cache-' + (Get-Date -Format 'yyyyMMdd-HHmmss') + '-' + [Guid]::NewGuid().ToString('N'))
$null = [IO.Directory]::CreateDirectory($backupDirectory)
foreach ($item in $items) {
    if (!$item.Exists) { continue }
    $backupPath = Join-Path $backupDirectory $item.BackupName
    [IO.File]::WriteAllBytes($backupPath, $item.Original)
    if ((Get-SeaPointHash ([IO.File]::ReadAllBytes($backupPath))) -ne $item.OriginalHash) {
        throw "A tide cache update backup did not pass verification. No project files changed. Backups: $backupDirectory"
    }
}
foreach ($item in $items) {
    $existsNow = Test-Path -LiteralPath $item.Path -PathType Leaf
    if ($existsNow -ne $item.Exists -or
        ($existsNow -and (Get-SeaPointHash ([IO.File]::ReadAllBytes($item.Path))) -ne $item.OriginalHash)) {
        throw "A SeaPoint file changed before installation. No files changed. Backups: $backupDirectory"
    }
}

try {
    foreach ($item in $items) {
        if ($item.OriginalHash -eq $item.PayloadHash) { continue }
        $null = [IO.Directory]::CreateDirectory([IO.Path]::GetDirectoryName($item.Path))
        # WRITE_TRIP_TARGET
        [IO.File]::WriteAllBytes($item.Path, $item.Payload)
        if ((Get-SeaPointHash ([IO.File]::ReadAllBytes($item.Path))) -ne $item.PayloadHash) {
            throw ('Installed ' + $item.Relative + ' did not pass verification.')
        }
    }
} catch {
    $installError = $_
    $restoreErrors = @()
    foreach ($item in $items) {
        try {
            if (!$item.Exists) {
                if (Test-Path -LiteralPath $item.Path -PathType Leaf) { [IO.File]::Delete($item.Path) }
                continue
            }
            [IO.File]::WriteAllBytes($item.Path, $item.Original)
            if ((Get-SeaPointHash ([IO.File]::ReadAllBytes($item.Path))) -ne $item.OriginalHash) {
                throw 'Restored file did not pass verification.'
            }
        } catch { $restoreErrors += ($item.Relative + ': ' + $_.ToString()) }
    }
    if ($restoreErrors.Count -gt 0) {
        throw "Tide cache update failed and an original file could not be restored. Restore the backups: $backupDirectory. Original error: $installError. Restore errors: $($restoreErrors -join '; ')"
    }
    throw "Tide cache update failed; the original files were restored. Backups: $backupDirectory. Original error: $installError"
}

Write-Host 'SeaPoint tide cache update installed.'
Write-Host ('Backups: ' + $backupDirectory)
Write-Host 'Run flutter analyze, then run SeaPoint on your connected Android phone.'

