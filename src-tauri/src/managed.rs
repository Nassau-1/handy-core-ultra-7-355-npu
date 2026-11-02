//! Build-time owner policy. User settings and local model discovery cannot expand it.
use once_cell::sync::Lazy;
use serde::Deserialize;

#[derive(Deserialize)]
struct Policy {
    managed: bool,
    default_model: String,
    allowed_models: Vec<String>,
}

static POLICY: Lazy<Policy> = Lazy::new(|| {
    serde_json::from_str(include_str!("../../packaging/managed-policy.json"))
        .expect("invalid embedded managed model policy")
});

pub fn enabled() -> bool {
    POLICY.managed
}

pub fn allows(id: &str) -> bool {
    !enabled() || POLICY.allowed_models.iter().any(|allowed| allowed == id)
}

pub fn require_allowed(id: &str) -> Result<(), String> {
    if allows(id) {
        Ok(())
    } else {
        Err("This model is not enabled in your organization's Handy distribution.".into())
    }
}

pub fn default_model() -> &'static str {
    &POLICY.default_model
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn managed_policy_denies_retired_downloaded_and_injected_models() {
        assert!(enabled());
        assert!(allows(default_model()));
        assert_eq!(POLICY.allowed_models.len(), 1);
        for id in [
            "openvino-turbo-int8-npu",
            "nemotron-35-npu-pilot",
            "turbo",
            "custom-model",
            "../model",
            "",
        ] {
            assert!(require_allowed(id).is_err(), "{id}");
        }
    }
}
