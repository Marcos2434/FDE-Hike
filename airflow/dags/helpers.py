import praw
import json

reddit_credentials = praw.Reddit(
    client_id="FmDPjXlF33v45zALJvQuEg",
    client_secret="-8egIOAFeqweAASt_NRUjVxPke5dyw",
    user_agent="hiking-app por u/Asteteh",
)

def call_redditt_api():


    nombre_excursion = "Yosemite"
    subreddit = reddit.subreddit("all")
    resultados_busqueda = subreddit.search(nombre_excursion, limit=5)

    publicaciones_principales = []

    for publicacion in resultados_busqueda:
        publicacion_principal = {
            "TÃ­tulo": publicacion.title,
            "Upvotes": publicacion.score,
            "Comentarios": []
        }

        publicacion.comments.replace_more(limit=None)

        for comentario in publicacion.comments.list():
            if hasattr(comentario, 'author'):
                datos_comentario = {
                    "Contenido": comentario.body,
                    "Upvotes": comentario.score
                }
                publicacion_principal["Comentarios"].append(datos_comentario)

        publicaciones_principales.append(publicacion_principal)

    # Order the main posts by upvotes in descending order
    publicaciones_principales.sort(key=lambda x: x["Upvotes"], reverse=True)

    # Capture the top 5 posts
    publicaciones = publicaciones_principales[:5]

    # Serialize the results in JSON format
    resultado_json = json.dumps(publicaciones, indent=4, ensure_ascii=False)

    with open("resultados.json", "w", encoding="utf-8") as archivo_json:
        archivo_json.write(resultado_json)


