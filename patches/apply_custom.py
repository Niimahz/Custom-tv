#!/usr/bin/env python3
from pathlib import Path
import sys
r=Path(sys.argv[1]); base=r/'on-tv/android/app/src/main/java/dev/couchtv/ontv'
def change(path,old,new):
 s=path.read_text()
 if s.count(old)!=1: raise RuntimeError(f'{path}: anchor count {s.count(old)} for {old[:60]!r}')
 path.write_text(s.replace(old,new,1))
fire=base/'FireHome.kt'
home=base/'HomeActivity.kt'
state="""
    private const val VISIT_PREFS = "custom_amazon_home"
    @Volatile private var amazonVisitPaused = false
    private fun paused(): Boolean {
        if (amazonVisitPaused) return true
        val p = App.instance.getSharedPreferences(VISIT_PREFS, android.content.Context.MODE_PRIVATE)
        if (!p.getBoolean("paused", false)) return false
        val oldBoot = p.getInt("boot_count", -1)
        val boot = runCatching { android.provider.Settings.Global.getInt(App.instance.contentResolver, "boot_count", -1) }.getOrDefault(-1)
        val oldEpoch = p.getLong("boot_epoch_ms", -1L)
        val epoch = System.currentTimeMillis() - android.os.SystemClock.elapsedRealtime()
        if ((oldBoot >= 0 && boot >= 0 && oldBoot != boot) ||
            (oldEpoch >= 0 && kotlin.math.abs(epoch-oldEpoch)>120000L)) {
            p.edit().clear().apply()
            return false
        }
        return true
    }
    fun pauseForAmazonVisit() {
        val boot = runCatching { android.provider.Settings.Global.getInt(App.instance.contentResolver, "boot_count", -1) }.getOrDefault(-1)
        App.instance.getSharedPreferences(VISIT_PREFS, android.content.Context.MODE_PRIVATE).edit()
            .putBoolean("paused", true).putInt("boot_count", boot)
            .putLong("boot_epoch_ms", System.currentTimeMillis()-android.os.SystemClock.elapsedRealtime()).commit()
        amazonVisitPaused = true
        recheck.removeCallbacks(again)
    }
    fun resumeFromAmazonVisit() {
        amazonVisitPaused = false
        App.instance.getSharedPreferences(VISIT_PREFS, android.content.Context.MODE_PRIVATE).edit().clear().apply()
        poke()
    }
"""
change(fire,'    @Volatile private var lastJump = 0L','    @Volatile private var lastJump = 0L\n'+state)
change(fire,'get() = isFireTv && App.homeEnabled(App.instance)','get() = isFireTv && App.homeEnabled(App.instance) && !paused()')
change(fire,'if (App.homeEnabled(App.instance) && cls in homeClasses) jump(force = true)','if (!paused() && App.homeEnabled(App.instance) && cls in homeClasses) jump(force = true)')
change(fire,'private fun jump(force: Boolean = false) {','private fun jump(force: Boolean = false) {\n        if (paused()) return')
change(home,'override fun onResume() { super.onResume(); front = true;','override fun onResume() { super.onResume(); FireHome.resumeFromAmazonVisit(); front = true;')
bridge="""
        @JavascriptInterface fun openAmazonHome(): Boolean {
            if (!FireHome.isFireTv) return false
            val intent = Intent(Intent.ACTION_MAIN).addCategory(Intent.CATEGORY_HOME)
                .setPackage(FireHome.AMAZON_HOME).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
            if (packageManager.resolveActivity(intent, 0) == null) return false
            main.post {
                FireHome.pauseForAmazonVisit()
                try { startActivity(intent) }
                catch (e: Exception) { FireHome.resumeFromAmazonVisit() }
            }
            return true
        }
"""
change(home,'    inner class Native {','    inner class Native {\n'+bridge)
print('Native patch applied')
