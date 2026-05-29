class_name ManifestLoader
extends RefCounted

const SUPPORTED_VERSIONS := [1]

static func load_file(path: String) -> Variant:
    if not FileAccess.file_exists(path):
        push_error("[manifest] file not found: %s" % path)
        return null
    var text := FileAccess.get_file_as_string(path)
    var json := JSON.new()
    var err := json.parse(text)
    if err != OK:
        push_error("[manifest] JSON parse error at line %d: %s" % [json.get_error_line(), json.get_error_message()])
        return null
    var data = json.data
    if typeof(data) != TYPE_DICTIONARY:
        push_error("[manifest] root must be object")
        return null
    return data

static func is_valid_version(data: Dictionary) -> bool:
    var v = data.get("version", 0)
    return int(v) in SUPPORTED_VERSIONS

static func section(data: Dictionary, name: String) -> Dictionary:
    var s = data.get(name, {})
    if typeof(s) != TYPE_DICTIONARY:
        return {}
    return s
