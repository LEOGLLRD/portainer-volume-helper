import datetime
import json
import os
import shutil
import random
import string
import patoolib
import stat
from django.http import FileResponse, Http404
from django.http import HttpResponseBadRequest
from django.http import JsonResponse, HttpResponse
from django.shortcuts import render, redirect
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.csrf import ensure_csrf_cookie

from .models import FileNode

BASE_DIR = '/volumes'


def extract_archive(request):
    if request.method == 'POST':
        archive_path = request.POST.get('archive_path')
        if not archive_path:
            return HttpResponseBadRequest("Chemin d'archive manquant.")

        archive_full_path = os.path.join(BASE_DIR, archive_path)
        print("archive_full_path :", archive_full_path)
        extract_to = os.path.dirname(archive_full_path)
        print("extract_to :", extract_to)

        try:
            patoolib.extract_archive(archive_full_path, outdir=extract_to)
        except Exception as e:
            print("Erreur lors de l'extraction :", e)
            return HttpResponseBadRequest("Erreur d'extraction.")

        return redirect('file_tree')

    return HttpResponseBadRequest("Méthode non autorisée.")


def get_octal_permissions(file_path):
    return oct(os.stat(file_path).st_mode)[-3:]


def octal_to_string(octal):
    result = ""
    value_letters = [(4, "r"), (2, "w"), (1, "x")]
    for digit in [int(n) for n in str(octal)]:
        for value, letter in value_letters:
            if digit >= value:
                result += letter
                digit -= value
            else:
                result += "-"
    return result


def get_directory_structure(rootdir):
    def build_tree(current_path, rel_path=""):
        tree = []
        try:
            for item in os.listdir(current_path):
                full_path = os.path.join(current_path, item)
                rel_item_path = os.path.join(rel_path, item)
                if os.path.isdir(full_path):
                    tree.append({
                        'name': item,
                        'full_path': rel_item_path,
                        'type': 'folder',
                        'rights': octal_to_string(get_octal_permissions(full_path)),
                        'lastmodified': datetime.datetime.fromtimestamp(os.path.getmtime(full_path)),
                        'children': build_tree(full_path, rel_item_path)
                    })
                else:
                    tree.append({
                        'name': item,
                        'full_path': rel_item_path,
                        'type': 'file',
                        'lastmodified': datetime.datetime.fromtimestamp(os.path.getmtime(full_path)),
                        'rights': octal_to_string(get_octal_permissions(full_path)),
                    })
        except PermissionError:
            pass
        return tree

    return build_tree(rootdir)


@csrf_exempt
def move_item(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        source = BASE_DIR + "/" + data.get("source_path")
        destination = BASE_DIR + "/" + data.get('destination_path')
        print(f'source: {source}, destination: {destination}')
        if source and destination:
            # On calcule le nouveau chemin final
            filename = os.path.basename(source)
            print(f'filename: {filename}')
            new_path = os.path.join(destination, filename)
            print(f"new_path: {new_path}")
            try:
                shutil.move(source, new_path)
                return JsonResponse({'status': 'success'})
            except Exception as e:
                print(e)
                return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

    return JsonResponse({'status': 'error', 'message': 'Invalid request'}, status=400)


@ensure_csrf_cookie
def file_tree_view(request):
    tree = get_directory_structure(BASE_DIR)
    return render(request, 'file_tree.html', {'tree': tree, 'root_name': os.path.basename(BASE_DIR)})


def download_file(request, path):
    file_path = os.path.join(BASE_DIR, path)
    if os.path.exists(file_path) and os.path.isfile(file_path):
        return FileResponse(open(file_path, 'rb'), as_attachment=True)
    raise Http404("Fichier non trouvé")


@csrf_protect
def upload_file(request):
    if request.method == 'POST':
        uploaded_file = request.FILES.get('file')
        target_path = request.POST.get('target_path', '').strip('/')

        if not uploaded_file:
            return HttpResponseBadRequest("Aucun fichier reçu.")

        # Construire le chemin complet
        save_path = os.path.join(BASE_DIR, target_path, uploaded_file.name)
        os.makedirs(os.path.dirname(save_path), exist_ok=True)

        with open(save_path, 'wb+') as destination:
            for chunk in uploaded_file.chunks():
                destination.write(chunk)

        return redirect('file_tree')  # Ou JsonResponse({'status': 'ok'}) si c’est AJAX

    return HttpResponseBadRequest("Méthode non autorisée.")


@csrf_exempt
def delete_item(request):
    if request.method == 'POST':
        try:
            if request.content_type != 'application/json':
                return JsonResponse({'status': 'error', 'message': 'Content-Type invalide'})

            data = json.loads(request.body)
            path = data.get('path')

            if not path:
                return JsonResponse({'status': 'error', 'message': 'Chemin manquant'})

            full_path = os.path.join(BASE_DIR, path)
            print("full_path", full_path)
            if os.path.exists(full_path):
                if os.path.isfile(full_path):
                    os.remove(full_path)
                elif os.path.isdir(full_path):
                    shutil.rmtree(full_path)
                else:
                    return JsonResponse({'status': 'error', 'message': 'Type de fichier inconnu'})
                return JsonResponse({'status': 'ok'})
            else:
                return JsonResponse({'status': 'error', 'message': 'Fichier ou dossier introuvable'})

        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)})
    else:
        return JsonResponse({'status': 'error', 'message': 'Méthode non autorisée'})


def create_folder(request):
    if request.method == 'POST':
        parent_path = request.POST.get('parent_path') or ''
        folder_name = request.POST.get('folder_name')

        # Crée le chemin complet
        full_path = os.path.join(parent_path, folder_name).strip("/")
        print(f"full path : {full_path}")

        # Crée le dossier physique
        os.makedirs(os.path.join("/volumes/", full_path), exist_ok=True)

        # Crée un nœud en base
        FileNode.objects.create(name=folder_name, type='folder', full_path=full_path)

        return redirect('file_tree')  # Adapte ce nom à ton URL


@csrf_exempt
def edit_file(request):
    if request.method == 'GET':
        print("GET")
        path = request.GET.get('path')
        full_path = os.path.join(BASE_DIR, path)
        print(f"full path : {full_path}")
        if os.path.exists(full_path):
            with open(full_path, 'r', encoding='utf-8') as f:
                return HttpResponse(f.read())
        return HttpResponseBadRequest("Fichier non trouvé.")

    elif request.method == 'POST':
        print("POST")
        data = json.loads(request.body)
        path = data.get('path')
        content = data.get('content')
        full_path = os.path.join(BASE_DIR, path)
        print(f"full path : {full_path}")
        try:
            with open(full_path, 'w', encoding='utf-8') as f:
                f.write(content)
            return JsonResponse({"status": "ok"})
        except Exception as e:
            return HttpResponseBadRequest(f"Erreur: {e}")


def login_view(request):
    error = None
    message = None
    if request.method == 'POST':
        input_password = request.POST.get('password')
        password_file = os.path.join('/volumes', 'key')

        try:
            with open(password_file, 'r') as f:
                stored_password = f.read().strip()
            if input_password == stored_password:
                request.session['authenticated'] = True
                return redirect('/files')
            else:
                error = "Mot de passe incorrect"
        except FileNotFoundError:
            print("No existing password file !")

            message = "Fichier de mot de passe introuvable, un nouveau mot de passe a été créé !"
            create_volume_file(f"{BASE_DIR}/key")
    return render(request, 'login.html', {'error': error, 'message': message})


def generate_random_string(length):
    return ''.join(random.choice(string.ascii_letters + string.digits) for _ in range(length))


def create_volume_file(path):
    random = generate_random_string(10)
    with open(path, 'w') as f:
        f.write(f"{random}")
