function App() {
  return (
    <div className="min-h-screen bg-gray-900 text-gray-100 p-6">
      <div className="max-w-2xl mx-auto">
        <h1 className="text-2xl font-bold text-violet-400 mb-2">
          Equestro Labs
        </h1>
        <p className="text-gray-400 mb-6">
          Stack: Tailwind CSS • Bootstrap • React. Use this app for dashboards or customer sites.
        </p>
        <div className="flex flex-wrap gap-3">
          <a
            href="/audit/dashboard"
            className="px-4 py-2 rounded-lg bg-violet-600 hover:bg-violet-500 text-white font-medium transition"
          >
            Website Audit
          </a>
          <a
            href="https://websites-natalie.onrender.com/audit/dashboard"
            target="_blank"
            rel="noopener noreferrer"
            className="px-4 py-2 rounded-lg border border-gray-600 hover:border-violet-500 text-gray-300 transition"
          >
            Audit on Render
          </a>
        </div>
      </div>
    </div>
  )
}

export default App
