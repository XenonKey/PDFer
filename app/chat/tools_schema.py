TOOLS = [
    {
        "name": "get_extraction_job_status",
        "description": (
            "Get the current status of a job by its id: the status itself (pending/processing/"
            "completed/failed/cancelled), its creation date, and the error message if it failed. "
            "Use this tool when the user asks about the status of a specific job."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "job_id": {
                    "type": "string",
                    "description": "UUID of the job to check the status of.",
                }
            },
            "required": ["job_id"],
        },
    }
]
