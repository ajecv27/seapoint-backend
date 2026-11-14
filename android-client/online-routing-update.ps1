# SeaPoint online routing update. Windows PowerShell 5.1 compatible.
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version 2.0
$utf8 = New-Object System.Text.UTF8Encoding($false, $true)
# Windows PowerShell 5.1 returns a top-level JSON array as one pipeline
# object. Assign that result first, then enumerate the variable explicitly.
$definitionJson = $utf8.GetString([Convert]::FromBase64String('W3sicGF0aCI6ImxpYi9uYXZpZ2F0aW9uX3NjcmVlbi5kYXJ0IiwiYmFja3VwX25hbWUiOiJuYXZpZ2F0aW9uX3NjcmVlbi5kYXJ0LmJhayIsIm1hcmtlcnMiOlsiY2xhc3MgTmF2aWdhdGlvblNjcmVlbiBleHRlbmRzIFN0YXRlZnVsV2lkZ2V0IiwiY2xhc3MgX05hdmlnYXRpb25TY3JlZW5TdGF0ZSJdLCJwYXRjaGVzIjpbeyJuYW1lIjoiaG9zdGVkLXJvdXRpbmctMSIsIm9sZCI6ImltcG9ydCAncGFja2FnZTpmbHV0dGVyL21hdGVyaWFsLmRhcnQnO1xuaW1wb3J0ICdwYWNrYWdlOmZsdXR0ZXJfY29tcGFzcy9mbHV0dGVyX2NvbXBhc3MuZGFydCc7XG5pbXBvcnQgJ3BhY2thZ2U6Z2VvbG9jYXRvci9nZW9sb2NhdG9yLmRhcnQnO1xuaW1wb3J0ICdwYWNrYWdlOmh0dHAvaHR0cC5kYXJ0JyBhcyBodHRwO1xuaW1wb3J0ICdwYWNrYWdlOm1hcGxpYnJlX2dsL21hcGxpYnJlX2dsLmRhcnQnO1xuaW1wb3J0ICdwYWNrYWdlOnBvaW50ZXJfaW50ZXJjZXB0b3IvcG9pbnRlcl9pbnRlcmNlcHRvci5kYXJ0JztcbmltcG9ydCAncGFja2FnZTp1cmxfbGF1bmNoZXIvdXJsX2xhdW5jaGVyLmRhcnQnO1xuXG5pbXBvcnQgJ2Z1ZWxfZG9ja3MuZGFydCc7XG5pbXBvcnQgJ3RyaXBfcmVjb3JkZXIuZGFydCc7XG5pbXBvcnQgJ3RyaXBfd2lkZ2V0cy5kYXJ0JztcbmltcG9ydCAndHJpcF9tYXAuZGFydCc7XG5pbXBvcnQgJ3RyaXBfam91cm5hbC5kYXJ0JztcbiIsIm5ldyI6ImltcG9ydCAncGFja2FnZTpmbHV0dGVyL21hdGVyaWFsLmRhcnQnO1xuaW1wb3J0ICdwYWNrYWdlOmZsdXR0ZXJfY29tcGFzcy9mbHV0dGVyX2NvbXBhc3MuZGFydCc7XG5pbXBvcnQgJ3BhY2thZ2U6Z2VvbG9jYXRvci9nZW9sb2NhdG9yLmRhcnQnO1xuaW1wb3J0ICdwYWNrYWdlOm1hcGxpYnJlX2dsL21hcGxpYnJlX2dsLmRhcnQnO1xuaW1wb3J0ICdwYWNrYWdlOnBvaW50ZXJfaW50ZXJjZXB0b3IvcG9pbnRlcl9pbnRlcmNlcHRvci5kYXJ0JztcbmltcG9ydCAncGFja2FnZTp1cmxfbGF1bmNoZXIvdXJsX2xhdW5jaGVyLmRhcnQnO1xuXG5pbXBvcnQgJ2Z1ZWxfZG9ja3MuZGFydCc7XG5pbXBvcnQgJ3RyaXBfcmVjb3JkZXIuZGFydCc7XG5pbXBvcnQgJ3JvdXRpbmdfYXBpLmRhcnQnO1xuaW1wb3J0ICd0cmlwX3dpZGdldHMuZGFydCc7XG5pbXBvcnQgJ3RyaXBfbWFwLmRhcnQnO1xuaW1wb3J0ICd0cmlwX2pvdXJuYWwuZGFydCc7XG4ifSx7Im5hbWUiOiJob3N0ZWQtcm91dGluZy0yIiwib2xkIjoiXG4gIHN0YXRpYyBjb25zdCBMYXRMbmcgX2FudGlndWFDZW50ZXIgPSBMYXRMbmcoMTcuMTIsIC02MS44MCk7XG5cbiAgLy8gQ2FuIGJlIGNoYW5nZWQgd2hlbiB0aGUgcm91dGluZyBzZXJ2aWNlIG1vdmVzIG9ubGluZS5cbiAgLy8gVGhpcyBhbHNvIGFsbG93cyBmdXR1cmUgZXhwYW5zaW9uIGJleW9uZCB0aGUgQ2FyaWJiZWFuLlxuICBzdGF0aWMgY29uc3QgU3RyaW5nIF9yb3V0aW5nVXJsT3ZlcnJpZGUgPVxuICBTdHJpbmcuZnJvbUVudmlyb25tZW50KCdTRUFQT0lOVF9ST1VUSU5HX1VSTCcpO1xuXG4gIFN0cmluZyBnZXQgX3JvdXRpbmdCYXNlVXJsIHtcbiAgICBpZiAoX3JvdXRpbmdVcmxPdmVycmlkZS5pc05vdEVtcHR5KSB7XG4gICAgICByZXR1cm4gX3JvdXRpbmdVcmxPdmVycmlkZS5yZXBsYWNlRmlyc3QoUmVnRXhwKHInLyskJyksICcnKTtcbiAgICB9XG5cbiAgICBpZiAoa0lzV2ViKSB7XG4gICAgICByZXR1cm4gJ2h0dHA6Ly9sb2NhbGhvc3Q6ODA4MCc7XG4gICAgfVxuXG4gICAgaWYgKGRlZmF1bHRUYXJnZXRQbGF0Zm9ybSA9PSBUYXJnZXRQbGF0Zm9ybS5hbmRyb2lkKSB7XG4gICAgICByZXR1cm4gJ2h0dHA6Ly8xMC4wLjIuMjo4MDgwJztcbiAgICB9XG5cbiAgICByZXR1cm4gJ2h0dHA6Ly9sb2NhbGhvc3Q6ODA4MCc7XG4gIH1cblxuICBzdGF0aWMgY29uc3QgU3RyaW5nIF9zYXRlbGxpdGVTdHlsZSA9IHInJydcbntcbiIsIm5ldyI6IlxuICBzdGF0aWMgY29uc3QgTGF0TG5nIF9hbnRpZ3VhQ2VudGVyID0gTGF0TG5nKDE3LjEyLCAtNjEuODApO1xuXG4gIC8vIEhvc3RlZCByb3V0aW5nIHdvcmtzIHdpdGhvdXQgYSBsYXB0b3A7IHJldGFpbiBhbiBleHBsaWNpdCBkZXZlbG9wZXIgb3ZlcnJpZGUuXG4gIHN0YXRpYyBjb25zdCBTdHJpbmcgX3JvdXRpbmdVcmxPdmVycmlkZSA9XG4gIFN0cmluZy5mcm9tRW52aXJvbm1lbnQoJ1NFQVBPSU5UX1JPVVRJTkdfVVJMJyk7XG5cbiAgU3RyaW5nIGdldCBfcm91dGluZ0Jhc2VVcmwgPT4gcm91dGluZ0Jhc2VVcmwoX3JvdXRpbmdVcmxPdmVycmlkZSk7XG5cbiAgc3RhdGljIGNvbnN0IFN0cmluZyBfc2F0ZWxsaXRlU3R5bGUgPSByJycnXG57XG4ifSx7Im5hbWUiOiJob3N0ZWQtcm91dGluZy0zIiwib2xkIjoiICAgIH0gY2F0Y2ggKGVycm9yLCBzdGFjaykge1xuICAgICAgX3RyaXBTYXZlRXJyb3IoZXJyb3IsIHN0YWNrKTtcbiAgICB9IGZpbmFsbHkge1xuICAgICAgaWYgKG1vdW50ZWQpIHNldFN0YXRlKCgpIHsgX3Jlc3RvcmluZ1RyaXAgPSBmYWxzZTsgfSk7XG4gICAgfVxuICB9XG5cbiIsIm5ldyI6IiAgICB9IGNhdGNoIChlcnJvciwgc3RhY2spIHtcbiAgICAgIF90cmlwU2F2ZUVycm9yKGVycm9yLCBzdGFjayk7XG4gICAgfSBmaW5hbGx5IHtcbiAgICAgIGlmIChtb3VudGVkKSB7IHNldFN0YXRlKCgpIHsgX3Jlc3RvcmluZ1RyaXAgPSBmYWxzZTsgfSk7IH1cbiAgICB9XG4gIH1cblxuIn0seyJuYW1lIjoiaG9zdGVkLXJvdXRpbmctNCIsIm9sZCI6IiAgICAgIF90cmFja2luZ1RyaXAgPSB0cmFja2luZztcbiAgICAgIF9sYXN0VHJpcFN1bW1hcnkgPSB0cmFja2luZyA/IG51bGwgOiBfdHJpcFJlY29yZGVyLnNuYXBzaG90KHNhdmVkLnNhdmVkQXQpO1xuICAgICAgX2xhc3RUcmlwQ2hlY2twb2ludCA9IERhdGVUaW1lLm5vdygpO1xuICAgICAgaWYgKHRyYWNraW5nKSBfbG9jYXRpb25TdGF0dXMgPSAnV2FpdGluZyBmb3IgZnJlc2ggR1BTIFx1MjAyMiBzYXZlZCB0cmlwIHJlc3RvcmVkJztcbiAgICB9KTtcbiAgICB1bmF3YWl0ZWQoX3JlZnJlc2hNYXBEYXRhKCkpO1xuICAgIHVuYXdhaXRlZChfcmVmcmVzaEN1cnJlbnRNYXJrZXIoKSk7XG4iLCJuZXciOiIgICAgICBfdHJhY2tpbmdUcmlwID0gdHJhY2tpbmc7XG4gICAgICBfbGFzdFRyaXBTdW1tYXJ5ID0gdHJhY2tpbmcgPyBudWxsIDogX3RyaXBSZWNvcmRlci5zbmFwc2hvdChzYXZlZC5zYXZlZEF0KTtcbiAgICAgIF9sYXN0VHJpcENoZWNrcG9pbnQgPSBEYXRlVGltZS5ub3coKTtcbiAgICAgIGlmICh0cmFja2luZykgeyBfbG9jYXRpb25TdGF0dXMgPSAnV2FpdGluZyBmb3IgZnJlc2ggR1BTIFx1MjAyMiBzYXZlZCB0cmlwIHJlc3RvcmVkJzsgfVxuICAgIH0pO1xuICAgIHVuYXdhaXRlZChfcmVmcmVzaE1hcERhdGEoKSk7XG4gICAgdW5hd2FpdGVkKF9yZWZyZXNoQ3VycmVudE1hcmtlcigpKTtcbiJ9LHsibmFtZSI6Imhvc3RlZC1yb3V0aW5nLTUiLCJvbGQiOiIgICAgaWYgKGNvbnRyb2xsZXIgPT0gbnVsbCkgcmV0dXJuO1xuXG4gICAgdHJ5IHtcbiAgICAgIGF3YWl0IGNvbnRyb2xsZXIuYWRkR2VvSnNvblNvdXJjZShcbiAgICAgICAgX3JvdXRlU291cmNlLFxuICAgICAgICBfZW1wdHlGZWF0dXJlQ29sbGVjdGlvbigpLFxuICAgICAgKTtcblxuICAgICAgYXdhaXQgY29udHJvbGxlci5hZGRMaW5lTGF5ZXIoXG4iLCJuZXciOiIgICAgaWYgKGNvbnRyb2xsZXIgPT0gbnVsbCkgcmV0dXJuO1xuXG4gICAgdHJ5IHtcbiAgICAgIGF3YWl0IGNvbnRyb2xsZXIuYWRkU291cmNlKFxuICAgICAgICBfcm91dGVTb3VyY2UsXG4gICAgICAgIEdlb2pzb25Tb3VyY2VQcm9wZXJ0aWVzKFxuICAgICAgICAgIGRhdGE6IF9lbXB0eUZlYXR1cmVDb2xsZWN0aW9uKCksXG4gICAgICAgICAgYXR0cmlidXRpb246ICdDb2FzdGxpbmU6IDxhIGhyZWY9XCJodHRwczovL3d3dy5vcGVuc3RyZWV0bWFwLm9yZy9jb3B5cmlnaHRcIj5cdTAwYTkgT3BlblN0cmVldE1hcCBjb250cmlidXRvcnM8L2E+OyAnXG4gICAgICAgICAgICAgICc8YSBocmVmPVwiaHR0cHM6Ly93d3cuc29lc3QuaGF3YWlpLmVkdS9wd2Vzc2VsL2dzaGhnL1wiPkdTSEhHPC9hPicsXG4gICAgICAgICksXG4gICAgICApO1xuXG4gICAgICBhd2FpdCBjb250cm9sbGVyLmFkZExpbmVMYXllcihcbiJ9LHsibmFtZSI6Imhvc3RlZC1yb3V0aW5nLTYiLCJvbGQiOiIgICAgKTtcblxuICAgIHRyeSB7XG4gICAgICBmaW5hbCByZXNwb25zZSA9IGF3YWl0IGh0dHBcbiAgICAgICAgICAuZ2V0KHVybClcbiAgICAgICAgICAudGltZW91dChjb25zdCBEdXJhdGlvbihzZWNvbmRzOiA2MCkpO1xuXG4gICAgICBmaW5hbCBkZWNvZGVkID0ganNvbkRlY29kZShyZXNwb25zZS5ib2R5KTtcblxuIiwibmV3IjoiICAgICk7XG5cbiAgICB0cnkge1xuICAgICAgZmluYWwgcmVzcG9uc2UgPSBhd2FpdCByZXF1ZXN0TWFyaW5lUm91dGUoXG4gICAgICAgIHVybCxcbiAgICAgICAgaXNDdXJyZW50OiAoKSA9PiBtb3VudGVkICYmIHJlcXVlc3RJZCA9PSBfcm91dGVSZXF1ZXN0SWQsXG4gICAgICApO1xuXG4gICAgICBmaW5hbCBkZWNvZGVkID0ganNvbkRlY29kZShyZXNwb25zZS5ib2R5KTtcblxuIn1dfSx7InBhdGgiOiJsaWIvcm91dGluZ19hcGkuZGFydCIsImJhY2t1cF9uYW1lIjoicm91dGluZ19hcGkuZGFydC5iYWsiLCJwYXlsb2FkIjoiYVcxd2IzSjBJQ2RrWVhKME9tRnplVzVqSnpzS2FXMXdiM0owSUNka1lYSjBPbU52Ym5abGNuUW5Pd29LYVcxd2IzSjBJQ2R3WVdOcllXZGxPbWgwZEhBdmFIUjBjQzVrWVhKMEp5QmhjeUJvZEhSd093b0tZMjl1YzNRZ2FHOXpkR1ZrVW05MWRHbHVaMVZ5YkNBOUlDZG9kSFJ3Y3pvdkwzTmxZWEJ2YVc1MExXSmhZMnRsYm1RdWIyNXlaVzVrWlhJdVkyOXRKenNLQ2xOMGNtbHVaeUJ5YjNWMGFXNW5RbUZ6WlZWeWJDaFRkSEpwYm1jZ2IzWmxjbkpwWkdVcElEMCtJRzkyWlhKeWFXUmxMbWx6Ulcxd2RIa0tJQ0FnSUQ4Z2FHOXpkR1ZrVW05MWRHbHVaMVZ5YkFvZ0lDQWdPaUJ2ZG1WeWNtbGtaUzV5WlhCc1lXTmxSbWx5YzNRb1VtVm5SWGh3S0hJbkx5c2tKeWtzSUNjbktUc0tDbU5zWVhOeklGSnZkWFJwYm1kU1pYRjFaWE4wUlhoalpYQjBhVzl1SUdsdGNHeGxiV1Z1ZEhNZ1JYaGpaWEIwYVc5dUlIc0tJQ0JqYjI1emRDQlNiM1YwYVc1blVtVnhkV1Z6ZEVWNFkyVndkR2x2YmloMGFHbHpMbTFsYzNOaFoyVXBPd29nSUdacGJtRnNJRk4wY21sdVp5QnRaWE56WVdkbE93b2dJRUJ2ZG1WeWNtbGtaUW9nSUZOMGNtbHVaeUIwYjFOMGNtbHVaeWdwSUQwK0lHMWxjM05oWjJVN0NuMEtDbU5zWVhOeklGSnZkWFJwYm1kU1pYRjFaWE4wUTJGdVkyVnNiR1ZrSUdsdGNHeGxiV1Z1ZEhNZ1JYaGpaWEIwYVc5dUlIdDlDZ292THk4Z1ZHaGxJSE5oYldVZ1NGUlVVRk1nWlc1a2NHOXBiblFnZDI5eWEzTWdiMjRnZEdobElIQm9iMjVsSUhkcGRHaHZkWFFnWVNCVlUwSWdZMjl1Ym1WamRHbHZiaUJ2Y2dvdkx5OGdiRzlqWVd3Z1JHOWphMlZ5SUhObGNuWnBZMlV1SUZKbGRISjVJRzl1YkhrZ1pYaHdiR2xqYVhSc2VTQjBjbUZ1YzJsbGJuUWdkMkZ5YldsdVp5OWlkWE41SUhKbGNHeHBaWE11Q2taMWRIVnlaVHhvZEhSd0xsSmxjM0J2Ym5ObFBpQnlaWEYxWlhOMFRXRnlhVzVsVW05MWRHVW9DaUFnVlhKcElIVnlhU3dnZXdvZ0lHaDBkSEF1UTJ4cFpXNTBQeUJqYkdsbGJuUXNDaUFnUkhWeVlYUnBiMjRnWW5Wa1oyVjBJRDBnWTI5dWMzUWdSSFZ5WVhScGIyNG9jMlZqYjI1a2N6b2dOVFVwTEFvZ0lFWjFkSFZ5WlR4MmIybGtQaUJHZFc1amRHbHZiaWhFZFhKaGRHbHZiaWsvSUhCaGRYTmxMQW9nSUdKdmIyd2dSblZ1WTNScGIyNG9LVDhnYVhORGRYSnlaVzUwTEFwOUtTQmhjM2x1WXlCN0NpQWdabWx1WVd3Z1kyOXVibVZqZEdsdmJpQTlJR05zYVdWdWRDQS9QeUJvZEhSd0xrTnNhV1Z1ZENncE93b2dJR1pwYm1Gc0lHVnNZWEJ6WldRZ1BTQlRkRzl3ZDJGMFkyZ29LUzR1YzNSaGNuUW9LVHNLSUNCbWFXNWhiQ0JrWld4aGVTQTlJSEJoZFhObElEOC9JRVoxZEhWeVpUeDJiMmxrUGk1a1pXeGhlV1ZrT3dvZ0lIUnllU0I3Q2lBZ0lDQm1iM0lnS0haaGNpQmhkSFJsYlhCMElEMGdNRHNnWVhSMFpXMXdkQ0E4SURFMk95QmhkSFJsYlhCMEt5c3BJSHNLSUNBZ0lDQWdhV1lnS0dselEzVnljbVZ1ZENBaFBTQnVkV3hzSUNZbUlDRnBjME4xY25KbGJuUW9LU2tnZEdoeWIzY2dVbTkxZEdsdVoxSmxjWFZsYzNSRFlXNWpaV3hzWldRb0tUc0tJQ0FnSUNBZ1ptbHVZV3dnY21WdFlXbHVhVzVuSUQwZ1luVmtaMlYwSUMwZ1pXeGhjSE5sWkM1bGJHRndjMlZrT3dvZ0lDQWdJQ0JwWmlBb2NtVnRZV2x1YVc1bklEdzlJRVIxY21GMGFXOXVMbnBsY204cElIUm9jbTkzSUZScGJXVnZkWFJGZUdObGNIUnBiMjRvSjFKdmRYUnBibWNnZEdsdFpXOTFkQ2NwT3dvZ0lDQWdJQ0JtYVc1aGJDQnlaWE53YjI1elpTQTlJR0YzWVdsMElHTnZibTVsWTNScGIyNHVaMlYwS0hWeWFTa3VkR2x0Wlc5MWRDaHlaVzFoYVc1cGJtY3BPd29nSUNBZ0lDQnBaaUFvYVhORGRYSnlaVzUwSUNFOUlHNTFiR3dnSmlZZ0lXbHpRM1Z5Y21WdWRDZ3BLU0IwYUhKdmR5QlNiM1YwYVc1blVtVnhkV1Z6ZEVOaGJtTmxiR3hsWkNncE93b2dJQ0FnSUNCa2VXNWhiV2xqSUdKdlpIazdDaUFnSUNBZ0lIUnllU0I3Q2lBZ0lDQWdJQ0FnWW05a2VTQTlJR3B6YjI1RVpXTnZaR1VvY21WemNHOXVjMlV1WW05a2VTazdDaUFnSUNBZ0lIMGdiMjRnUm05eWJXRjBSWGhqWlhCMGFXOXVJSHNLSUNBZ0lDQWdJQ0IwYUhKdmR5QmpiMjV6ZENCU2IzVjBhVzVuVW1WeGRXVnpkRVY0WTJWd2RHbHZiaWdLSUNBZ0lDQWdJQ0FnSUNkVWFHVWdjbTkxZEdsdVp5QnpaWEoyYVdObElHTnZkV3hrSUc1dmRDQnlaWE53YjI1a0xpQlFiR1ZoYzJVZ2RISjVJR0ZuWVdsdUlITm9iM0owYkhrdUp5d0tJQ0FnSUNBZ0lDQXBPd29nSUNBZ0lDQjlDaUFnSUNBZ0lHWnBibUZzSUhKbGRISjVJRDBLSUNBZ0lDQWdJQ0FnSUNoeVpYTndiMjV6WlM1emRHRjBkWE5EYjJSbElEMDlJRFF5T1NCOGZDQnlaWE53YjI1elpTNXpkR0YwZFhORGIyUmxJRDA5SURVd015a2dKaVlLSUNBZ0lDQWdJQ0FnSUNBZ0lDQmliMlI1SUdseklFMWhjQ0FtSmdvZ0lDQWdJQ0FnSUNBZ0lDQWdJR0p2WkhsYkozSmxkSEo1WVdKc1pTZGRJRDA5SUhSeWRXVTdDaUFnSUNBZ0lHbG1JQ2doY21WMGNua2dmSHdnWVhSMFpXMXdkQ0E5UFNBeE5Ta2djbVYwZFhKdUlISmxjM0J2Ym5ObE93b2dJQ0FnSUNCbWFXNWhiQ0J6ZFdkblpYTjBaV1FnUFNCaWIyUjVXeWR5WlhSeWVWOWhablJsY2w5ekoxMDdDaUFnSUNBZ0lHWnBibUZzSUhObFkyOXVaSE1nUFNCemRXZG5aWE4wWldRZ2FYTWdiblZ0SUQ4Z2MzVm5aMlZ6ZEdWa0xuUnZTVzUwS0NrdVkyeGhiWEFvTVN3Z015a2dPaUF5T3dvZ0lDQWdJQ0JtYVc1aGJDQjNZV2wwSUQwZ1JIVnlZWFJwYjI0b2MyVmpiMjVrY3pvZ2MyVmpiMjVrY3lrN0NpQWdJQ0FnSUdsbUlDaGxiR0Z3YzJWa0xtVnNZWEJ6WldRZ0t5QjNZV2wwSUQ0OUlHSjFaR2RsZENrZ2NtVjBkWEp1SUhKbGMzQnZibk5sT3dvZ0lDQWdJQ0JoZDJGcGRDQmtaV3hoZVNoM1lXbDBLVHNLSUNBZ0lIMEtJQ0FnSUhSb2NtOTNJR052Ym5OMElGSnZkWFJwYm1kU1pYRjFaWE4wUlhoalpYQjBhVzl1S0FvZ0lDQWdJQ0FnSUNkU2IzVjBhVzVuSUdseklHSjFjM2t1SUZCc1pXRnpaU0IwY25rZ1lXZGhhVzRnYzJodmNuUnNlUzRuS1RzS0lDQjlJRzl1SUZScGJXVnZkWFJGZUdObGNIUnBiMjRnZXdvZ0lDQWdkR2h5YjNjZ1kyOXVjM1FnVW05MWRHbHVaMUpsY1hWbGMzUkZlR05sY0hScGIyNG9DaUFnSUNBZ0lDZFNiM1YwYVc1bklHbHpJSFJoYTJsdVp5QjBiMjhnYkc5dVp5NGdRMmhsWTJzZ2VXOTFjaUJqYjI1dVpXTjBhVzl1SUdGdVpDQjBjbmtnWVdkaGFXNHVKeXdLSUNBZ0lDazdDaUFnZlNCdmJpQm9kSFJ3TGtOc2FXVnVkRVY0WTJWd2RHbHZiaUI3Q2lBZ0lDQjBhSEp2ZHlCamIyNXpkQ0JTYjNWMGFXNW5VbVZ4ZFdWemRFVjRZMlZ3ZEdsdmJpZ0tJQ0FnSUNBZ0owTnZkV3hrSUc1dmRDQmpiMjV1WldOMElIUnZJSEp2ZFhScGJtY3VJRU5vWldOcklIbHZkWElnYVc1MFpYSnVaWFFnWTI5dWJtVmpkR2x2YmlCaGJtUWdkSEo1SUdGbllXbHVMaWNzQ2lBZ0lDQXBPd29nSUgwZ1ptbHVZV3hzZVNCN0NpQWdJQ0JwWmlBb1kyeHBaVzUwSUQwOUlHNTFiR3dwSUdOdmJtNWxZM1JwYjI0dVkyeHZjMlVvS1RzS0lDQjlDbjBLIiwic2hhMjU2IjoiNGU0OGFmYmI0OTA0NTJhYmQyNTA3NTI1YjU3MzRjN2U2NjE5M2M3NzYzNmRhODc3MGQ0Yzc0ZTg5MGQ5NTdjZiJ9XQ=='))
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
            throw 'The online routing patch definition is invalid. No files changed.'
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
# Confirm that the phone will have a working online planner before editing.
Write-Host 'Checking hosted SeaPoint routing. A sleeping server may take a moment to wake.'
[Net.ServicePointManager]::SecurityProtocol = [Net.ServicePointManager]::SecurityProtocol -bor [Net.SecurityProtocolType]::Tls12
$cloudReady = $false
$cloudClock = [Diagnostics.Stopwatch]::StartNew()
for ($attempt = 0; $attempt -lt 10; $attempt++) {
    $remaining = 90 - [int]$cloudClock.Elapsed.TotalSeconds
    if ($remaining -le 0) { break }
    try {
        $health = Invoke-RestMethod -Uri 'https://seapoint-backend.onrender.com/routing/health' -TimeoutSec ([Math]::Min(60, $remaining))
        if ($health.status -eq 'ready' -and
            $health.service -eq 'seapoint-marine-routing' -and
            $health.routing_build -eq 'seapoint-hosted-caribbean-v1' -and
            $health.coastline_dataset -eq 'caribbean-osm-gshhg-20261114-v1' -and
            $health.depth_checked -eq $false) {
            $cloudReady = $true
            break
        }
    } catch { }
    if ($attempt -lt 9) { Start-Sleep -Seconds 2 }
}
if (!$cloudReady) {
    throw 'Hosted routing is not ready. No project files changed. Please try again shortly.'
}
Write-Host 'Hosted Caribbean routing is ready.'

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
    Write-Host 'The SeaPoint online routing update is already installed. Stop the app and click Run in Android Studio to load it on your phone.'

    return
}
foreach ($item in $items) {
    $existsNow = Test-Path -LiteralPath $item.Path -PathType Leaf
    if ($existsNow -ne $item.Exists -or
        ($existsNow -and (Get-SeaPointHash ([IO.File]::ReadAllBytes($item.Path))) -ne $item.OriginalHash)) {
        throw 'A SeaPoint file changed while the update was being prepared. No files changed.'
    }
}

$backupDirectory = Join-Path $projectRoot ('.seapoint-backups/online-routing-' + (Get-Date -Format 'yyyyMMdd-HHmmss') + '-' + [Guid]::NewGuid().ToString('N'))
$null = [IO.Directory]::CreateDirectory($backupDirectory)
foreach ($item in $items) {
    if (!$item.Exists) { continue }
    $backupPath = Join-Path $backupDirectory $item.BackupName
    [IO.File]::WriteAllBytes($backupPath, $item.Original)
    if ((Get-SeaPointHash ([IO.File]::ReadAllBytes($backupPath))) -ne $item.OriginalHash) {
        throw "A online routing update backup did not pass verification. No project files changed. Backups: $backupDirectory"
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
        throw "Online routing update failed and an original file could not be restored. Restore the backups: $backupDirectory. Original error: $installError. Restore errors: $($restoreErrors -join '; ')"
    }
    throw "Online routing update failed; the original files were restored. Backups: $backupDirectory. Original error: $installError"
}

Write-Host 'SeaPoint online routing update installed.'
Write-Host ('Backups: ' + $backupDirectory)
Write-Host 'Run flutter analyze, then run SeaPoint on your connected Android phone.'

