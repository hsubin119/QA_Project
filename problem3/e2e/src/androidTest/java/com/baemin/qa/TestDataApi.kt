package com.baemin.qa

import androidx.test.platform.app.InstrumentationRegistry
import java.net.HttpURLConnection
import java.net.URLEncoder
import java.net.URL
import java.nio.charset.StandardCharsets
import java.util.concurrent.Executors
import java.util.concurrent.TimeUnit

class TestDataApi private constructor(
    private val baseUrl: String,
    private val token: String,
) {
    fun clearCart() = delete("/test-support/cart")

    fun cancelOrder(orderId: String) {
        val encodedOrderId = URLEncoder.encode(orderId, StandardCharsets.UTF_8.name())
        delete("/test-support/orders/$encodedOrderId")
    }

    private fun delete(path: String) {
        val executor = Executors.newSingleThreadExecutor()
        try {
            executor.submit {
                val connection = URL("${baseUrl.trimEnd('/')}$path")
                    .openConnection() as HttpURLConnection
                try {
                    connection.requestMethod = "DELETE"
                    connection.connectTimeout = TIMEOUT_MILLIS
                    connection.readTimeout = TIMEOUT_MILLIS
                    connection.setRequestProperty("X-Test-Token", token)

                    check(connection.responseCode in 200..299) {
                        "Test data cleanup failed: DELETE $path returned ${connection.responseCode}"
                    }
                } finally {
                    connection.disconnect()
                }
            }.get(TIMEOUT_SECONDS, TimeUnit.SECONDS)
        } finally {
            executor.shutdownNow()
        }
    }

    companion object {
        private const val TIMEOUT_MILLIS = 5_000
        private const val TIMEOUT_SECONDS = 10L

        fun fromInstrumentationArguments(): TestDataApi {
            val arguments = InstrumentationRegistry.getArguments()
            val baseUrl = requireNotNull(arguments.getString("testDataApiUrl")) {
                "Instrumentation argument testDataApiUrl is required"
            }
            val token = requireNotNull(arguments.getString("testDataApiToken")) {
                "Instrumentation argument testDataApiToken is required"
            }
            return TestDataApi(baseUrl, token)
        }
    }
}
