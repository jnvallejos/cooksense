# Phase 4 Spec — Android App (Quick Recipe + Meal Plan flows)

**Repo:** `cooksense` (public monorepo, `android/` directory)
**Domain:** Mobile client consuming CookSense backend
**Stack:** Kotlin 1.9+, Jetpack Compose, Hilt, Retrofit, CameraX, DataStore, Coroutines, JUnit5, Turbine, MockK
**Approach:** Test-Driven Development, granular commits, feature branch + PR
**Branch:** `phase-4-android`

---

## 1. Goal of Phase 4

The largest phase. Build the full Android app consuming Phase 1-3 backend endpoints. Onboarding, camera capture, ingredient review, recipe search results, recipe detail with Q&A, meal plan, shopping list, profile settings. Bilingual ES/EN. Tested.

At the end of Phase 4:
- App builds and installs on Android emulator (API 26+)
- All 9 user-facing screens implemented
- Network layer with Retrofit, error handling, retry on transient failures
- Local persistence via DataStore (anonymous user_id, profile cache, last meal plan)
- ViewModels tested with Turbine + MockK (~80% coverage on business logic)
- Integration tests with MockWebServer for the network layer
- Bilingual string resources (ES/EN)
- Phase 0 hello world replaced by real onboarding entry point
- Backend Phase 0-3 code unchanged

---

## 2. Solution & Folder Structure

```
android/
├── app/
│   ├── src/
│   │   ├── main/
│   │   │   ├── java/com/cooksense/
│   │   │   │   ├── CookSenseApplication.kt              (NEW, @HiltAndroidApp)
│   │   │   │   ├── MainActivity.kt                      (replaced)
│   │   │   │   ├── di/
│   │   │   │   │   ├── NetworkModule.kt                 (NEW)
│   │   │   │   │   ├── PersistenceModule.kt             (NEW)
│   │   │   │   │   └── RepositoryModule.kt              (NEW)
│   │   │   │   ├── data/
│   │   │   │   │   ├── api/
│   │   │   │   │   │   ├── CookSenseApi.kt              (NEW, Retrofit interface)
│   │   │   │   │   │   ├── dto/
│   │   │   │   │   │   │   ├── ProfileDto.kt
│   │   │   │   │   │   │   ├── RecipeDto.kt
│   │   │   │   │   │   │   ├── SearchDto.kt
│   │   │   │   │   │   │   ├── VisionDto.kt
│   │   │   │   │   │   │   ├── QuestionDto.kt
│   │   │   │   │   │   │   ├── MealPlanDto.kt
│   │   │   │   │   │   │   ├── ShoppingDto.kt
│   │   │   │   │   │   │   └── ErrorDto.kt
│   │   │   │   │   │   └── ApiResult.kt                 (Result<T> wrapper)
│   │   │   │   │   ├── repository/
│   │   │   │   │   │   ├── ProfileRepository.kt
│   │   │   │   │   │   ├── RecipeRepository.kt
│   │   │   │   │   │   ├── VisionRepository.kt
│   │   │   │   │   │   └── MealPlanRepository.kt
│   │   │   │   │   └── local/
│   │   │   │   │       ├── UserPreferences.kt           (DataStore wrapper)
│   │   │   │   │       └── ProfileCache.kt
│   │   │   │   ├── domain/
│   │   │   │   │   ├── model/
│   │   │   │   │   │   ├── Profile.kt
│   │   │   │   │   │   ├── Recipe.kt
│   │   │   │   │   │   ├── Ingredient.kt
│   │   │   │   │   │   ├── MealPlan.kt
│   │   │   │   │   │   ├── ShoppingList.kt
│   │   │   │   │   │   └── DomainError.kt
│   │   │   │   │   └── usecase/
│   │   │   │   │       ├── EnsureUserIdUseCase.kt
│   │   │   │   │       ├── SaveProfileUseCase.kt
│   │   │   │   │       ├── ExtractIngredientsUseCase.kt
│   │   │   │   │       ├── SearchRecipesUseCase.kt
│   │   │   │   │       ├── AskRecipeQuestionUseCase.kt
│   │   │   │   │       ├── GenerateMealPlanUseCase.kt
│   │   │   │   │       └── GetShoppingListUseCase.kt
│   │   │   │   ├── ui/
│   │   │   │   │   ├── theme/
│   │   │   │   │   │   ├── Color.kt
│   │   │   │   │   │   ├── Theme.kt
│   │   │   │   │   │   └── Type.kt
│   │   │   │   │   ├── navigation/
│   │   │   │   │   │   ├── CookSenseNavGraph.kt
│   │   │   │   │   │   └── Route.kt
│   │   │   │   │   ├── onboarding/
│   │   │   │   │   │   ├── OnboardingScreen.kt
│   │   │   │   │   │   ├── OnboardingViewModel.kt
│   │   │   │   │   │   └── OnboardingState.kt
│   │   │   │   │   ├── home/
│   │   │   │   │   │   ├── HomeScreen.kt
│   │   │   │   │   │   ├── HomeViewModel.kt
│   │   │   │   │   │   └── HomeState.kt
│   │   │   │   │   ├── camera/
│   │   │   │   │   │   ├── CameraScreen.kt
│   │   │   │   │   │   ├── CameraViewModel.kt
│   │   │   │   │   │   ├── CameraState.kt
│   │   │   │   │   │   └── CameraXBindings.kt
│   │   │   │   │   ├── ingredients/
│   │   │   │   │   │   ├── IngredientsReviewScreen.kt
│   │   │   │   │   │   ├── IngredientsReviewViewModel.kt
│   │   │   │   │   │   └── IngredientsReviewState.kt
│   │   │   │   │   ├── recipes/
│   │   │   │   │   │   ├── RecipeListScreen.kt
│   │   │   │   │   │   ├── RecipeListViewModel.kt
│   │   │   │   │   │   ├── RecipeListState.kt
│   │   │   │   │   │   ├── RecipeDetailScreen.kt
│   │   │   │   │   │   ├── RecipeDetailViewModel.kt
│   │   │   │   │   │   └── RecipeDetailState.kt
│   │   │   │   │   ├── mealplan/
│   │   │   │   │   │   ├── MealPlanScreen.kt
│   │   │   │   │   │   ├── MealPlanViewModel.kt
│   │   │   │   │   │   └── MealPlanState.kt
│   │   │   │   │   ├── shopping/
│   │   │   │   │   │   ├── ShoppingListScreen.kt
│   │   │   │   │   │   ├── ShoppingListViewModel.kt
│   │   │   │   │   │   └── ShoppingListState.kt
│   │   │   │   │   ├── profile/
│   │   │   │   │   │   ├── ProfileScreen.kt
│   │   │   │   │   │   ├── ProfileViewModel.kt
│   │   │   │   │   │   └── ProfileState.kt
│   │   │   │   │   └── components/
│   │   │   │   │       ├── ErrorBanner.kt
│   │   │   │   │       ├── LoadingIndicator.kt
│   │   │   │   │       ├── IngredientChip.kt
│   │   │   │   │       └── RecipeCard.kt
│   │   │   │   └── util/
│   │   │   │       ├── DispatchersProvider.kt
│   │   │   │       └── Logger.kt
│   │   │   ├── res/
│   │   │   │   ├── values/strings.xml                   (English defaults)
│   │   │   │   ├── values-es/strings.xml                (Spanish overrides)
│   │   │   │   ├── values/themes.xml
│   │   │   │   ├── drawable/                            (icons, illustrations)
│   │   │   │   └── mipmap-*/                            (launcher icons)
│   │   │   └── AndroidManifest.xml                      (extended)
│   │   └── test/
│   │       └── java/com/cooksense/
│   │           ├── data/
│   │           │   ├── api/
│   │           │   │   └── CookSenseApiTest.kt
│   │           │   ├── repository/
│   │           │   │   ├── ProfileRepositoryTest.kt
│   │           │   │   ├── RecipeRepositoryTest.kt
│   │           │   │   ├── VisionRepositoryTest.kt
│   │           │   │   └── MealPlanRepositoryTest.kt
│   │           │   └── local/
│   │           │       ├── UserPreferencesTest.kt
│   │           │       └── ProfileCacheTest.kt
│   │           ├── domain/
│   │           │   └── usecase/
│   │           │       ├── EnsureUserIdUseCaseTest.kt
│   │           │       ├── SaveProfileUseCaseTest.kt
│   │           │       ├── ExtractIngredientsUseCaseTest.kt
│   │           │       ├── SearchRecipesUseCaseTest.kt
│   │           │       ├── AskRecipeQuestionUseCaseTest.kt
│   │           │       ├── GenerateMealPlanUseCaseTest.kt
│   │           │       └── GetShoppingListUseCaseTest.kt
│   │           └── ui/
│   │               ├── onboarding/OnboardingViewModelTest.kt
│   │               ├── home/HomeViewModelTest.kt
│   │               ├── camera/CameraViewModelTest.kt
│   │               ├── ingredients/IngredientsReviewViewModelTest.kt
│   │               ├── recipes/RecipeListViewModelTest.kt
│   │               ├── recipes/RecipeDetailViewModelTest.kt
│   │               ├── mealplan/MealPlanViewModelTest.kt
│   │               ├── shopping/ShoppingListViewModelTest.kt
│   │               └── profile/ProfileViewModelTest.kt
│   ├── build.gradle.kts                                  (extended)
│   └── proguard-rules.pro
└── (root unchanged)
```

---

## 3. Architecture

### 3.1 Layers

Strict 3-layer separation:

- **`data/`**: Retrofit API, DTOs, repositories, DataStore. Network and persistence.
- **`domain/`**: Pure Kotlin business logic. Use cases, domain models, error types. No Android dependencies.
- **`ui/`**: Compose screens, ViewModels, navigation. Depends on `domain/`, never on `data/` directly.

ViewModels invoke use cases. Use cases call repositories. Repositories call API + local storage.

### 3.2 Result type for use cases

```kotlin
// domain/model/UseCaseResult.kt
sealed class UseCaseResult<out T> {
    data class Success<T>(val value: T) : UseCaseResult<T>()
    data class Failure(val error: DomainError) : UseCaseResult<Nothing>()
}

// domain/model/DomainError.kt
sealed class DomainError {
    data class Network(val cause: Throwable?) : DomainError()
    data class Server(val statusCode: Int, val message: String) : DomainError()
    data class Validation(val field: String, val message: String) : DomainError()
    data object NotFound : DomainError()
    data object Forbidden : DomainError()
    data object RateLimitExceeded : DomainError()
    data object Unknown : DomainError()
}
```

This mirrors the backend's `Result<T>` pattern. Mobile maps server `Error.Code` strings to `DomainError` types in the repository layer.

### 3.3 ViewModel state pattern

Each ViewModel exposes a single `StateFlow<State>` representing the screen's full state. State is a sealed interface or data class with explicit Loading/Error/Success cases when relevant.

Example:

```kotlin
// ui/recipes/RecipeListState.kt
sealed interface RecipeListState {
    data object Idle : RecipeListState
    data object Loading : RecipeListState
    data class Success(val recipes: List<Recipe>) : RecipeListState
    data class Error(val message: String, val isRetryable: Boolean) : RecipeListState
}
```

ViewModels use `viewModelScope` for coroutines. Screens collect with `collectAsStateWithLifecycle`.

---

## 4. Network Layer

### 4.1 `CookSenseApi.kt`

Retrofit interface mapping each backend endpoint:

```kotlin
interface CookSenseApi {

    @POST("api/profile")
    suspend fun upsertProfile(
        @Header("X-User-Id") userId: String,
        @Body profile: ProfileRequestDto,
    ): Response<ProfileResponseDto>

    @GET("api/profile/{user_id}")
    suspend fun getProfile(
        @Header("X-User-Id") userId: String,
        @Path("user_id") userIdPath: String,
    ): Response<ProfileResponseDto>

    @POST("api/recipes/search")
    suspend fun searchRecipes(
        @Header("X-User-Id") userId: String,
        @Body request: SearchRequestDto,
    ): Response<SearchResponseDto>

    @Multipart
    @POST("api/vision/extract-ingredients")
    suspend fun extractIngredients(
        @Header("X-User-Id") userId: String,
        @Part image: MultipartBody.Part,
    ): Response<VisionResponseDto>

    @POST("api/recipes/{recipe_id}/ask")
    suspend fun askRecipeQuestion(
        @Header("X-User-Id") userId: String,
        @Path("recipe_id") recipeId: String,
        @Body request: QuestionRequestDto,
    ): Response<QuestionResponseDto>

    @POST("api/meal-plan/generate")
    suspend fun generateMealPlan(
        @Header("X-User-Id") userId: String,
        @Body request: MealPlanRequestDto,
    ): Response<MealPlanResponseDto>

    @POST("api/meal-plan/{plan_id}/shopping")
    suspend fun getShoppingList(
        @Header("X-User-Id") userId: String,
        @Path("plan_id") planId: String,
    ): Response<ShoppingListResponseDto>
}
```

### 4.2 `NetworkModule.kt`

Hilt module providing `OkHttpClient`, `Retrofit`, and `CookSenseApi`. Configures:
- Connection timeout: 10s
- Read timeout: 30s (vision endpoint can take 5-10s on cold backend)
- Logging interceptor in debug builds only
- `BACKEND_URL` from `BuildConfig` (set via `local.properties`)
- kotlinx.serialization JSON converter

### 4.3 Error mapping

The repository layer translates HTTP errors and `ErrorDto` (from backend's `ErrorResponse`) into `DomainError`:

```kotlin
private fun mapError(response: Response<*>, errorBody: ErrorDto?): DomainError {
    return when (response.code()) {
        400 -> when (errorBody?.code) {
            "Profile.NotFound" -> DomainError.Validation("profile", "Profile not set")
            "Validation.IngredientsEmpty" -> DomainError.Validation("ingredients", errorBody.message)
            else -> DomainError.Validation("unknown", errorBody?.message ?: "Bad request")
        }
        403 -> DomainError.Forbidden
        404 -> DomainError.NotFound
        429 -> DomainError.RateLimitExceeded
        in 500..599 -> DomainError.Server(response.code(), errorBody?.message ?: "Server error")
        else -> DomainError.Unknown
    }
}
```

### 4.4 Retry policy

Single retry on `IOException` (network) at the repository level. No retry on 4xx. No retry on 5xx (let user retry manually). Vision and meal plan endpoints have no retry — they cost money on the backend.

---

## 5. Local Persistence

### 5.1 `UserPreferences.kt`

DataStore Preferences for:

- `user_id`: anonymous UUID, generated on first launch and persisted forever
- `language`: "en" or "es", set during onboarding
- `onboarding_completed`: Boolean
- `last_known_profile`: serialized Profile (JSON) for offline display

```kotlin
class UserPreferences(private val dataStore: DataStore<Preferences>) {
    val userId: Flow<String> = dataStore.data.map { it[USER_ID_KEY] ?: generateAndPersistUserId() }
    val language: Flow<String> = dataStore.data.map { it[LANGUAGE_KEY] ?: deviceDefaultLanguage() }
    val onboardingCompleted: Flow<Boolean> = dataStore.data.map { it[ONBOARDING_KEY] ?: false }

    suspend fun setUserId(userId: String) { ... }
    suspend fun setLanguage(language: String) { ... }
    suspend fun setOnboardingCompleted(completed: Boolean) { ... }
}
```

### 5.2 `ProfileCache.kt`

In-memory cache (singleton scoped via Hilt) holding the last-fetched `Profile`. Refreshed on profile updates. Survives across screens; lost on process death (which is fine; backend is the source of truth).

### 5.3 No image persistence

Captured images are processed in-memory and discarded after upload. No gallery, no history, no thumbnails. Privacy-friendly and matches backend behavior.

---

## 6. Screens

### 6.1 Onboarding (4-5 screens)

Sequential flow:

1. **Welcome screen**: app name, tagline, "Get started" button
2. **Cooking for**: radio buttons (Just me / Couple / Family of N with stepper)
3. **Dietary restrictions**: checkbox list (gluten-free, vegan, vegetarian, lactose-free, none)
4. **Goals**: radio (None / Lose weight / Build muscle / Eat better) + cooking skill (Beginner/Intermediate/Pro)
5. **Time budget**: radio (15min / 30min / 45min / 60min) + language toggle (auto/EN/ES)

On completion:
- Generate user_id (if not exists)
- POST profile to backend
- Set `onboarding_completed = true`
- Navigate to Home

`OnboardingViewModel` exposes a single `OnboardingState` with current step + accumulated form data. Validation per step. Back button supported.

### 6.2 Home

Two big buttons:
- "Quick Recipe" -> camera flow -> ingredient review -> recipe list
- "Plan 3 Days" -> camera flow -> ingredient review -> meal plan

Below, optional: "Last meal plan" card if a plan exists in local cache.

### 6.3 Camera

Uses CameraX. Preview, capture button, retry button. After capture, show confirmation thumbnail, then upload.

Permissions handled via `accompanist-permissions` or built-in `rememberLauncherForActivityResult`.

`CameraViewModel` manages capture state: `Idle`, `Capturing`, `Captured(bytes)`, `Uploading`, `Done(IngredientsResponse)`, `Error`.

### 6.4 Ingredients Review

Shows detected ingredients as chips. User can:
- Tap to remove
- Tap "+" to add manually (text field with autocomplete from common ingredients list, V1 = no autocomplete; just text input)
- Tap "Find recipes" or "Plan 3 days" depending on flow context

### 6.5 Recipe List

After search, show recipes as cards with:
- Title
- Time, match %, fitness badge if profile has goal
- Personalized note (truncated)

Tap a card -> Recipe Detail.

### 6.6 Recipe Detail

Full recipe view:
- Title, full personalized description
- Ingredients (highlight which user has)
- Steps (numbered)
- Estimated time, nutrition (if available)
- "Ask a question" button -> opens modal/sheet

Q&A in a `BottomSheet`. Text field, send button. Conversation accumulates locally (not persisted across navigation).

### 6.7 Meal Plan

3 day tabs (Day 1, Day 2, Day 3). Each shows breakfast/lunch/dinner cards.
Top section: scores (reuse, variety, macro alignment) as small badges.
Bottom button: "Generate shopping list" -> Shopping List screen.

Tap a recipe card -> Recipe Detail (same screen as Recipe List flow).

### 6.8 Shopping List

Items grouped by category (vegetable, protein, etc.). Each item shows name, estimated quantity, count of recipes needing it.
"Mark all as bought" button (V1: just visual checkbox state, not persisted across sessions).

### 6.9 Profile

Settings screen. Edit any profile field. Save button -> POST to backend.
Bottom: "Reset app" (clears DataStore, restarts onboarding). Useful for demo.

---

## 7. Navigation

`Navigation Compose`. Single `NavHost` in MainActivity.

```kotlin
sealed class Route(val path: String) {
    data object Onboarding : Route("onboarding")
    data object Home : Route("home")
    data object Camera : Route("camera/{flow}") {
        fun build(flow: CaptureFlow) = "camera/${flow.name}"
    }
    data object IngredientsReview : Route("ingredients_review")
    data object RecipeList : Route("recipe_list")
    data object RecipeDetail : Route("recipe_detail/{recipeId}") {
        fun build(recipeId: String) = "recipe_detail/$recipeId"
    }
    data object MealPlan : Route("meal_plan/{planId}") {
        fun build(planId: String) = "meal_plan/$planId"
    }
    data object ShoppingList : Route("shopping/{planId}") {
        fun build(planId: String) = "shopping/$planId"
    }
    data object Profile : Route("profile")
}

enum class CaptureFlow { QuickRecipe, MealPlan }
```

Start destination logic: if `onboarding_completed` is false -> `Onboarding`. Else -> `Home`.

State sharing between camera -> ingredients review -> recipes/meal plan: use `SavedStateHandle` and a shared ViewModel scoped to the navigation graph or pass minimal data via route arguments. Avoid global singletons.

---

## 8. Strings (i18n)

`res/values/strings.xml` (English):

```xml
<resources>
    <string name="app_name">CookSense</string>
    <string name="onboarding_welcome_title">Welcome to CookSense</string>
    <string name="onboarding_welcome_tagline">A photo of your pantry. Recipes you can actually make.</string>
    <string name="onboarding_cta_get_started">Get started</string>
    <string name="onboarding_cooking_for_title">Who are you cooking for?</string>
    <string name="cooking_for_self">Just me</string>
    <string name="cooking_for_couple">Couple</string>
    <string name="cooking_for_family">Family</string>
    <!-- ... full strings.xml has ~80 entries -->
</resources>
```

`res/values-es/strings.xml` (Spanish overrides). Same keys, translated values.

Profile language setting controls Spanish or English. Backend respects `language` field; mobile resource resolution respects device locale by default but can be overridden via `Locale` in the Application context if user picks different language than device.

V1 simplification: device locale auto-detected. Profile.language sent to backend. UI strings follow device locale (Android default behavior).

---

## 9. Dependency Injection

Hilt modules:

### 9.1 `NetworkModule.kt`

```kotlin
@Module
@InstallIn(SingletonComponent::class)
object NetworkModule {

    @Provides
    @Singleton
    fun provideJson(): Json = Json {
        ignoreUnknownKeys = true
        coerceInputValues = true
    }

    @Provides
    @Singleton
    fun provideOkHttpClient(): OkHttpClient {
        return OkHttpClient.Builder()
            .connectTimeout(10, TimeUnit.SECONDS)
            .readTimeout(30, TimeUnit.SECONDS)
            .apply {
                if (BuildConfig.DEBUG) {
                    addInterceptor(HttpLoggingInterceptor().apply { level = BODY })
                }
            }
            .build()
    }

    @Provides
    @Singleton
    fun provideRetrofit(json: Json, client: OkHttpClient): Retrofit {
        return Retrofit.Builder()
            .baseUrl(BuildConfig.BACKEND_URL)
            .client(client)
            .addConverterFactory(json.asConverterFactory("application/json".toMediaType()))
            .build()
    }

    @Provides
    @Singleton
    fun provideApi(retrofit: Retrofit): CookSenseApi = retrofit.create()
}
```

### 9.2 `PersistenceModule.kt`

Provides `DataStore<Preferences>` singleton.

### 9.3 `RepositoryModule.kt`

Binds repository implementations to interfaces (since use cases depend on interfaces, not concrete repos).

---

## 10. Test Strategy — Phase 4

### 10.1 Categories

- **ViewModel tests** (Turbine + MockK): one test class per ViewModel, ~5-10 tests each
- **Use case tests** (MockK): pure business logic, fast
- **Repository tests** (MockWebServer): real Retrofit + DTO serialization, mocked HTTP
- **Local persistence tests**: real DataStore with `TemporaryFolder`

No instrumented tests in this Phase. UI tests deferred (Phase 5 if needed). Pure JVM tests run fast in CI.

### 10.2 ViewModel test pattern

```kotlin
class RecipeListViewModelTest {

    private val searchUseCase: SearchRecipesUseCase = mockk()
    private val testDispatcher = StandardTestDispatcher()

    private fun createViewModel() = RecipeListViewModel(
        searchUseCase = searchUseCase,
        dispatchers = TestDispatchersProvider(testDispatcher),
    )

    @Test
    fun `loadRecipes emits Loading then Success on happy path`() = runTest(testDispatcher) {
        val recipes = listOf(Recipe(...), Recipe(...))
        coEvery { searchUseCase(any()) } returns UseCaseResult.Success(recipes)

        val vm = createViewModel()
        vm.state.test {
            assertThat(awaitItem()).isInstanceOf(RecipeListState.Idle::class)
            vm.loadRecipes(listOf("tomato", "basil"))
            assertThat(awaitItem()).isInstanceOf(RecipeListState.Loading::class)
            val success = awaitItem() as RecipeListState.Success
            assertThat(success.recipes).hasSize(2)
        }
    }

    @Test
    fun `loadRecipes emits Error on network failure`() = runTest(testDispatcher) {
        coEvery { searchUseCase(any()) } returns UseCaseResult.Failure(DomainError.Network(null))

        val vm = createViewModel()
        vm.state.test {
            awaitItem() // Idle
            vm.loadRecipes(listOf("x"))
            awaitItem() // Loading
            val error = awaitItem() as RecipeListState.Error
            assertThat(error.isRetryable).isTrue()
        }
    }
}
```

### 10.3 Tests by file

**Use cases (one happy path + one error path each, ~14 tests):**

```
EnsureUserIdUseCaseTest:
  - returns existing user_id when present
  - generates new user_id when missing

SaveProfileUseCaseTest:
  - calls repository.saveProfile and returns Success
  - returns Failure when repository throws

ExtractIngredientsUseCaseTest:
  - returns ingredients on success
  - returns RateLimitExceeded when 429
  - returns Network on IOException

SearchRecipesUseCaseTest:
  - returns recipes on success
  - returns Validation when ingredients empty
  - returns Network on connection failure

AskRecipeQuestionUseCaseTest:
  - returns answer on success
  - returns NotFound when recipe missing
  - returns RateLimitExceeded when 429

GenerateMealPlanUseCaseTest:
  - returns plan on success
  - returns RateLimitExceeded when daily plan limit hit
  - returns Validation when ingredients empty

GetShoppingListUseCaseTest:
  - returns list on success
  - returns Forbidden for other-user plan
  - returns NotFound for unknown plan
```

**ViewModels (~50 tests across 9 ViewModels):**

```
OnboardingViewModelTest:
  - starts at step Welcome
  - advances to next step on continue
  - validates household size required
  - emits ProfileSaved on completion
  - shows error if backend fails

HomeViewModelTest:
  - shows last meal plan if exists
  - hides last plan card when no plans cached

CameraViewModelTest:
  - state transitions Idle -> Capturing -> Captured
  - upload triggers Uploading state
  - upload success transitions to Done
  - upload failure emits Error

IngredientsReviewViewModelTest:
  - removes ingredient on tap
  - adds ingredient via add()
  - validates non-empty list before submit
  - emits Submitted with ingredients on submit

RecipeListViewModelTest:
  - loadRecipes emits Loading then Success
  - emits Error on network failure
  - emits Error with rate limit message on 429
  - filters by max time when filter applied

RecipeDetailViewModelTest:
  - loads recipe by id
  - askQuestion emits Asking then Success
  - askQuestion preserves previous Q&A in context
  - askQuestion emits Error on rate limit

MealPlanViewModelTest:
  - loadOrGenerate emits Loading then Success on generation
  - selectDay updates current day index
  - emits Error with rate limit message

ShoppingListViewModelTest:
  - loads list by plan id
  - groups items by category
  - emits Forbidden when not owner
  - toggleBought updates UI state

ProfileViewModelTest:
  - loads current profile on init
  - saveProfile emits Saving then Saved
  - emits Error on validation failure
```

**Repository tests with MockWebServer (~30 tests across 4 repositories):**

```
ProfileRepositoryTest:
  - upsertProfile sends correct DTO and returns Success
  - upsertProfile maps 400 to Validation error
  - upsertProfile maps 500 to Server error
  - getProfile returns profile on 200
  - getProfile maps 404 to NotFound

(similar for RecipeRepositoryTest, VisionRepositoryTest, MealPlanRepositoryTest)
```

**Local persistence tests (~5 tests):**

```
UserPreferencesTest:
  - userId returns persisted value
  - userId generates new UUID when not present
  - setLanguage persists value
  - onboardingCompleted defaults to false

ProfileCacheTest:
  - get returns null when not set
  - get returns cached profile after set
  - clear empties cache
```

**Total: ~100-110 tests for Phase 4.**

### 10.4 Test infrastructure

`TestDispatchersProvider` swaps `Dispatchers.Main/IO` with a `StandardTestDispatcher` for predictable coroutine ordering.

`MockWebServer` for repository tests: a real HTTP server on localhost, controllable per-test responses.

```kotlin
class TestDispatchersProvider(testDispatcher: TestDispatcher) : DispatchersProvider {
    override val main = testDispatcher
    override val io = testDispatcher
    override val default = testDispatcher
}
```

---

## 11. Commit Convention — Phase 4

Granular commits, ~70-80 expected for Phase 4 (largest phase). Examples:

```
chore(android): add hilt application class and DI scaffold
chore(android): add network DI module with retrofit and okhttp
chore(android): add persistence DI module with datastore
chore(android): add repository DI module
chore(android): add CookSenseApi retrofit interface
chore(android): add API DTOs for profile, search, vision
chore(android): add API DTOs for question, meal plan, shopping
chore(android): add ApiResult sealed type for response wrapping
chore(android): add domain models for profile, recipe, ingredient
chore(android): add domain models for meal plan, shopping list
chore(android): add DomainError sealed hierarchy
chore(android): add UseCaseResult sealed type
test(android): add SearchRecipesUseCase happy path test
feat(android): implement SearchRecipesUseCase with network mapping
test(android): add SearchRecipesUseCase error mapping tests
feat(android): map 429 to RateLimitExceeded in SearchRecipesUseCase
test(android): add ExtractIngredientsUseCase tests
feat(android): implement ExtractIngredientsUseCase with multipart
test(android): add AskRecipeQuestionUseCase tests
feat(android): implement AskRecipeQuestionUseCase with previous context
test(android): add GenerateMealPlanUseCase tests
feat(android): implement GenerateMealPlanUseCase
test(android): add GetShoppingListUseCase tests
feat(android): implement GetShoppingListUseCase
test(android): add EnsureUserIdUseCase tests
feat(android): implement EnsureUserIdUseCase with DataStore
test(android): add SaveProfileUseCase tests
feat(android): implement SaveProfileUseCase
test(android): add ProfileRepository tests with MockWebServer
feat(android): implement ProfileRepository
test(android): add RecipeRepository tests
feat(android): implement RecipeRepository with error mapping
test(android): add VisionRepository tests
feat(android): implement VisionRepository with multipart upload
test(android): add MealPlanRepository tests
feat(android): implement MealPlanRepository
test(android): add UserPreferences tests
feat(android): implement UserPreferences with DataStore
test(android): add ProfileCache tests
feat(android): implement ProfileCache singleton
chore(android): add app theme, color palette, typography
chore(android): add navigation graph and routes
chore(android): add string resources EN and ES
test(android): add OnboardingViewModel tests
feat(android): implement OnboardingViewModel state machine
chore(android): add OnboardingScreen composables for steps 1-5
test(android): add HomeViewModel tests
feat(android): implement HomeViewModel
chore(android): add HomeScreen composable
test(android): add CameraViewModel tests
feat(android): implement CameraViewModel
chore(android): add CameraScreen composable with CameraX bindings
test(android): add IngredientsReviewViewModel tests
feat(android): implement IngredientsReviewViewModel
chore(android): add IngredientsReviewScreen with chip list
test(android): add RecipeListViewModel tests
feat(android): implement RecipeListViewModel
chore(android): add RecipeListScreen with cards
test(android): add RecipeDetailViewModel tests
feat(android): implement RecipeDetailViewModel with Q&A state
chore(android): add RecipeDetailScreen with Q&A bottom sheet
test(android): add MealPlanViewModel tests
feat(android): implement MealPlanViewModel
chore(android): add MealPlanScreen with day tabs
test(android): add ShoppingListViewModel tests
feat(android): implement ShoppingListViewModel with category grouping
chore(android): add ShoppingListScreen
test(android): add ProfileViewModel tests
feat(android): implement ProfileViewModel with edit save flow
chore(android): add ProfileScreen
chore(android): wire MainActivity to NavGraph with start destination logic
chore(android): replace HelloScreen with onboarding entry
chore(android): add error banner and loading components
docs: add Phase 4 progress note to README
```

~75-80 commits expected.

---

## 12. What NOT to Do in Phase 4

- **Do not** modify Phase 0-3 backend code. The mobile app consumes existing endpoints.
- **Do not** add iOS code. Phase 6.
- **Do not** add instrumented (androidTest) UI tests. JVM ViewModel tests are enough for Phase 4. Espresso and Compose UI tests can land in Phase 5 if needed.
- **Do not** add a Room database. DataStore is sufficient for V1 persistence needs.
- **Do not** add image compression libraries beyond what CameraX provides. Standard JPEG capture is fine.
- **Do not** add image filters, cropping, or editing. V1 is "tap to capture, send."
- **Do not** add OAuth, Google Sign-In, or any auth provider. Anonymous user IDs only.
- **Do not** add deep links. V1 navigation is in-app only.
- **Do not** add push notifications. V1 is purely interactive.
- **Do not** add analytics SDKs (Firebase, Mixpanel, etc.). V1 is privacy-clean.
- **Do not** add crash reporting (Crashlytics, Sentry). Phase 5 may add it.
- **Do not** add app shortcuts, widgets, tile services. V1 launches via icon only.
- **Do not** add tablet-specific layouts. V1 is phone portrait only.
- **Do not** add dark mode override. Follow system setting (Material 3 default).
- **Do not** add custom fonts beyond Material 3 typography. System font is fine.
- **Do not** add animations beyond `animateContentSize` and basic transitions. V1 is functional, not flashy.
- **Do not** add background services or workers. V1 is foreground-only.
- **Do not** add "share to other apps" intents. V1 is contained.
- **Do not** add account migration paths. There's no account; just user_id.
- **Do not** add image caching (Coil disk cache beyond defaults). Recipes don't have images in V1; cards are text-only.
- **Do not** add NPM, Node, or any JS tooling.

---

## 13. Acceptance Criteria for Phase 4 Completion

- [ ] `./gradlew assembleDebug` succeeds
- [ ] `./gradlew testDebugUnitTest` returns green with 100+ tests
- [ ] `./gradlew ktlintCheck detekt` clean
- [ ] App installs on emulator (API 26+) and launches without crash
- [ ] Onboarding flow completes and persists profile
- [ ] Home screen reachable after onboarding
- [ ] Camera capture works (real device or emulator with virtual camera)
- [ ] Ingredient review allows add/remove
- [ ] Recipe list loads from backend (real or stub backend)
- [ ] Recipe detail shows full info, Q&A modal opens and submits
- [ ] Meal plan screen shows 3 days, scores visible
- [ ] Shopping list groups items by category
- [ ] Profile screen edits and saves
- [ ] Bilingual: switching device locale to Spanish reflects translated strings
- [ ] All error states handled gracefully (network failure, rate limit, 404, 403)
- [ ] DataStore persists user_id across app restarts
- [ ] Phase 0-3 backend code unchanged in this PR's diff
- [ ] Phase 0 hello world replaced; old `HelloScreen.kt` removed
- [ ] Android CI workflow green
- [ ] PR opened on `phase-4-android` against `main`, NOT merged

---

## 14. Branch & PR Workflow — Phase 4

1. `git checkout -b phase-4-android` from `main`
2. Commit on branch following Section 11
3. `git push -u origin phase-4-android`
4. `gh pr create --base main --head phase-4-android --title "Phase 4: Android App"`
5. PR body: summary + acceptance criteria + screenshots from emulator + "What's deferred to Phase 5": polish, Internal Testing release, deployment
6. NOT merge.
7. Report and stop.

---

## 15. Handoff to Phase 5 (preview)

Phase 5 finalizes the project for portfolio:

- Backend deployed to Fly.io (production environment)
- Android APK signed and uploaded to Google Play Internal Testing
- README rewritten for portfolio audience (architecture diagram, demo video, Why this design)
- CI workflows finalized (deploy on merge to main)
- LICENSE final
- Demo video filmed and embedded
- "Defendable in interview" final pass

Phase 4 ships the working app. Phase 5 ships it to the world.
