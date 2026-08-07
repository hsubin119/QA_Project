package com.baemin.qa

import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.filters.LargeTest
import androidx.test.platform.app.InstrumentationRegistry
import androidx.test.uiautomator.UiDevice
import com.baemin.qa.pages.CartPage
import com.baemin.qa.pages.MenuPage
import com.baemin.qa.pages.OrderStatusPage
import com.baemin.qa.pages.PaymentPage
import com.baemin.qa.pages.ShopListPage
import org.junit.Before
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith

@LargeTest
@RunWith(AndroidJUnit4::class)
class OrderFlowTest {
    private lateinit var device: UiDevice

    @get:Rule
    val failureArtifacts = FailureArtifactsRule()

    @Before
    fun setUp() {
        val instrumentation = InstrumentationRegistry.getInstrumentation()
        device = UiDevice.getInstance(instrumentation)

        // 로그인된 테스트 계정과 주문 가능한 테스트 매장은 CI fixture에서 준비한다.
        // 각 Page Object의 waitUntilLoaded가 잘못된 시작 화면을 즉시 식별한다.
        ShopListPage(device).waitUntilLoaded()
    }

    @Test
    fun paidOrderMovesToWaitingForAcceptance() {
        ShopListPage(device).openShop(TEST_SHOP_NAME)

        MenuPage(device)
            .waitUntilLoaded()
            .addMenu(TEST_MENU_NAME)

        CartPage(device)
            .waitUntilLoaded()
            .assertSelectedMenu(TEST_MENU_NAME)
            .placeOrder()

        val orderId = PaymentPage(device)
            .waitUntilLoaded()
            .pay()

        OrderStatusPage(device)
            .waitUntilLoaded()
            .assertOrderId(orderId)
            .assertStatus(WAITING_FOR_ACCEPTANCE)
            .assertPaymentCompleted()
            .assertNoBlockingError()
    }

    private companion object {
        const val TEST_SHOP_NAME = "치킨 테스트 매장"
        const val TEST_MENU_NAME = "후라이드"
        const val WAITING_FOR_ACCEPTANCE = "접수 대기"
    }
}
