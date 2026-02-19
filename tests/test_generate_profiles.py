"""Tests for the industry profile registry."""

from __future__ import annotations

import pytest

from context_cli.core.generate.profiles import (
    BLOG_PROFILE,
    CPG_PROFILE,
    ECOMMERCE_PROFILE,
    GENERIC_PROFILE,
    SAAS_PROFILE,
    Profile,
    get_profile,
    list_profiles,
    register_profile,
)


class TestProfileDataclass:
    def test_generic_has_required_fields(self):
        assert GENERIC_PROFILE.name == "generic"
        assert GENERIC_PROFILE.display_name == "Generic"
        assert len(GENERIC_PROFILE.schema_types) > 0
        assert len(GENERIC_PROFILE.llms_txt_sections) > 0

    def test_cpg_profile(self):
        assert CPG_PROFILE.name == "cpg"
        assert "Product" in CPG_PROFILE.schema_types
        assert "Brand Story" in CPG_PROFILE.llms_txt_sections

    def test_saas_profile(self):
        assert SAAS_PROFILE.name == "saas"
        assert "SoftwareApplication" in SAAS_PROFILE.schema_types
        assert "API Reference" in SAAS_PROFILE.llms_txt_sections

    def test_ecommerce_profile(self):
        assert ECOMMERCE_PROFILE.name == "ecommerce"
        assert "Offer" in ECOMMERCE_PROFILE.schema_types
        assert "Shipping & Returns" in ECOMMERCE_PROFILE.llms_txt_sections

    def test_blog_profile(self):
        assert BLOG_PROFILE.name == "blog"
        assert "Article" in BLOG_PROFILE.schema_types
        assert "About the Author" in BLOG_PROFILE.llms_txt_sections

    def test_all_profiles_have_descriptions(self):
        all_profiles = [
            GENERIC_PROFILE, CPG_PROFILE, SAAS_PROFILE, ECOMMERCE_PROFILE, BLOG_PROFILE
        ]
        for profile in all_profiles:
            assert profile.description, f"{profile.name} has no description"

    def test_keywords_default_empty_for_generic(self):
        assert GENERIC_PROFILE.keywords == []

    def test_keywords_populated_for_cpg(self):
        assert len(CPG_PROFILE.keywords) > 0


class TestGetProfile:
    def test_get_existing(self):
        profile = get_profile("generic")
        assert profile is GENERIC_PROFILE

    def test_get_all_names(self):
        for name in ["generic", "cpg", "saas", "ecommerce", "blog"]:
            profile = get_profile(name)
            assert profile.name == name

    def test_get_nonexistent_raises(self):
        with pytest.raises(KeyError, match="Unknown profile 'nonexistent'"):
            get_profile("nonexistent")


class TestListProfiles:
    def test_returns_all_five(self):
        profiles = list_profiles()
        assert len(profiles) >= 5

    def test_names_unique(self):
        profiles = list_profiles()
        names = [p.name for p in profiles]
        assert len(names) == len(set(names))


class TestRegisterProfile:
    def test_register_custom(self):
        custom = Profile(
            name="healthcare",
            display_name="Healthcare",
            description="For healthcare sites.",
            schema_types=["Organization", "MedicalOrganization"],
            llms_txt_sections=["Services", "Patient Resources"],
        )
        register_profile(custom)
        assert get_profile("healthcare") is custom

    def test_register_overwrites(self):
        original_count = len(list_profiles())
        custom = Profile(
            name="healthcare",
            display_name="Healthcare v2",
            description="Updated healthcare.",
            schema_types=["Organization"],
            llms_txt_sections=["Services"],
        )
        register_profile(custom)
        assert get_profile("healthcare").display_name == "Healthcare v2"
        # Should not increase count since we replaced
        assert len(list_profiles()) == original_count
