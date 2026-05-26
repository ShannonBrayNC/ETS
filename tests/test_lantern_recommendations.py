from ets.lantern import (
    LanternRecommendationStatus,
    LanternRecommendationUpdateRequest,
    build_recommendation_export,
    default_ets_recommendations,
    recommendation_duplicate_key,
    update_recommendation,
)


def test_recommendation_export_includes_sprint_candidates_and_duplicate_keys():
    recommendations = default_ets_recommendations()

    export = build_recommendation_export(recommendations)

    assert export.owner_repo == "ShannonBrayNC/ETS"
    assert len(export.recommendations) >= 3
    assert len(export.sprint_candidates) == len(export.recommendations)
    first = export.recommendations[0]
    assert first.duplicate_key == recommendation_duplicate_key(
        first.owner_repo,
        first.item_type,
        first.title,
    )
    assert first.tracking_issue_url is not None


def test_recommendation_update_appends_review_note():
    recommendation = default_ets_recommendations()[0]

    updated = update_recommendation(
        recommendation,
        LanternRecommendationUpdateRequest(
            status=LanternRecommendationStatus.IN_REVIEW,
            note="Selected for Christina review.",
            author="christina",
        ),
    )

    assert updated.status == LanternRecommendationStatus.IN_REVIEW
    assert updated.review_notes[0].author == "christina"
    assert updated.review_notes[0].note == "Selected for Christina review."
