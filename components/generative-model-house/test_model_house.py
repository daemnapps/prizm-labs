import unittest
import model_house as MH


class ModelHouse(unittest.TestCase):
    def test_every_picture_and_edit_is_gpt_image_on_the_higgsfield_command_line(self):
        for job in ("pictures.generate", "pictures.edit"):
            got = MH.model(job)
            self.assertEqual((got["registry_id"], got["door"], got["model"]), ("gpt-image-2.5", "higgsfield", "gpt_image_2_5"))

    def test_the_clip_model_is_seedance_and_omni_is_gone(self):
        self.assertEqual(MH.model("clips.seedance")["id"], "seedance_2_5")
        for gone in ("clips.omni", "clips.omni_google", "sound.omni_voice"):
            with self.assertRaises(KeyError):
                MH.model(gone)

    def test_an_unknown_job_is_refused(self):
        with self.assertRaises(KeyError):
            MH.model("clips.kling")

    def test_the_picture_ladder_is_three_models_on_higgsfield_then_openai_as_the_last_rung(self):
        self.assertEqual([MH.model(j)["model"] for j in ("pictures.generate", "pictures.backup", "pictures.object")],
                         ["gpt_image_2_5", "seedream_v5_pro", "nano_banana_pro"])
        for j in ("pictures.generate", "pictures.edit", "pictures.backup", "pictures.object"):
            self.assertEqual(MH.model(j)["door"], "higgsfield", j)
        net = MH.model("pictures.safety_net")
        self.assertEqual((net["registry_id"], net["door"]), ("gpt-image-2.5", "openai"))

    def test_the_fal_overflow_is_retired(self):
        with self.assertRaises(KeyError):
            MH.model("pictures.overflow")
        self.assertNotIn("fal", {MH.model(j)["door"] for j in ("pictures.generate", "pictures.edit", "pictures.backup", "pictures.object")})

    # MDL-8 (registry-linked house), 2026-10-22: assertions added, none changed.
    def test_the_judge_and_the_local_tools_stay_bare_strings(self):
        self.assertEqual(MH.model("behind.judge"), "gemini-3.1-pro-preview")
        self.assertEqual(MH.model("behind.upscale"), "real-esrgan (local)")
        self.assertEqual(MH.model("behind.3d"), "trellis.2 (local)")

    def test_every_model_job_names_a_registry_id_not_a_vendor_string(self):
        for section in ("pictures", "clips", "swipe_footage"):
            for job, row in MH.house()[section].items():
                if job.startswith("ruled_"):          # a ruling block, not a job
                    continue
                self.assertIn("registry", row, f"{section}.{job}")
                self.assertNotIn("model", row, f"{section}.{job}")
                self.assertNotIn("id", row, f"{section}.{job}")

    def test_choices_lead_with_the_house_default(self):
        self.assertEqual(MH.choices("pictures.edit")[0]["reason"], "house default")


if __name__ == "__main__":
    unittest.main()
