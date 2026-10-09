# ActionPilot UI captures

These screenshots show the existing Streamlit application with synthetic demo data.
Home reads current owned order records and delivery availability. The screenshot
preview does not write to the database. No statistics or testimonials are fabricated.

- [Home — desktop](home-desktop.png): full Home page at 1440px width.
- [Home — mobile](home-mobile.png): stacked page at 390px width.
- [AI Assistant — desktop](assistant-desktop.png): assistant and manual support panels.
- [Dashboard — desktop](dashboard-desktop.png): owned orders and delivery planning.
- [Delivery confirmation — UI test](confirmation-ui-test.png): clearly labeled mocked
  AI transport, with the actual synthetic database and proposal/confirmation service.

The ordinary assistant capture shows the honest missing-key state. The UI test
capture uses a temporary test harness outside the application, never a product
mock mode. Live OpenAI requests require configured credentials; no live request
was used to produce these captures. The automated suite and browser check cover
confirmation, cancellation, customer switching and stale proposal rejection.

Full-page captures use taller viewports to show the whole page. Browser layout
checks also verified 1366×768 laptop and 390×844 mobile viewports without horizontal
overflow, with the laptop chat composer visible before scrolling.
