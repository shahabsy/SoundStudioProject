import jsonschema

PROJECT_SCHEMA = {
    "type": "object",
    "properties": {
        "project_name": {"type": "string"},
        "created": {"type": "string"},
        "imported_files": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "file_name": {"type": "string"},
                    "file_path": {"type": "string"},
                    "imported_time": {"type": "string"}
                },
                "required": ["file_name", "file_path", "imported_time"],
                "additionalProperties": False
            }  
        },
        "imported_sounds": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "audio_id": {"type": "string"},
                    "url": {"type": "string"},
                    "data": {
                        "type": "object",
                        "properties": {
                            "resourceType": {"type": "string"},
                            "options": {
                                "type": "object",
                                "properties": {
                                    "name": {"type": "string"},
                                    "asset_type": {"type": "string"},
                                    "loop": {"type": "boolean"},
                                    "singleInstance": {"type": "boolean"},
                                    "volume": {"type": "number"},
                                    "fade_in": {"type": ["string", "number"]},
                                    "fade_out": {"type": ["string", "number"]}
                                },
                                "required": ["name", "asset_type", "loop", "singleInstance", "volume", "fade_in", "fade_out"],
                                "additionalProperties": False
                            }
                        },
                        "required": ["resourceType", "options"],
                        "additionalProperties": False
                    }
                },
                "required": ["audio_id", "url", "data"],
                "additionalProperties": False
            }
        },
        "last_saved": {"type": "string"},
        "project_path": {"type": "string"}
    },
    "required": ["project_name", "imported_files", "imported_sounds", "project_path"]
}

def validate_project_metadata(metadata):
    try:
        jsonschema.validate(instance=metadata, schema=PROJECT_SCHEMA)
        return True, None
    except jsonschema.ValidationError as e:
        return False, str(e)